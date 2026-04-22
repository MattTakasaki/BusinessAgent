# ============================================================
# middleware/rate_limiter.py
# Per-tenant rate limiting based on plan tier.
#
# How it works:
#   - Every agent call increments a Redis counter for the tenant
#   - Counter key includes the billing period (month)
#   - If counter exceeds plan limit → 429 response
#   - Redis counters sync to Postgres tenant_usage periodically
#   - On Redis miss (cold start), falls back to Postgres count
# ============================================================

import os
import redis
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# ---- Redis client (Upstash uses rediss:// for TLS) ----
redis_client = redis.from_url(
    os.environ.get("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True
)

# ---- Supabase client ----
supabase: Client = create_client(
    os.environ.get("SUPABASE_URL", ""),
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
)

# ---- Plan limits (mirrors plan_limits table) ----
PLAN_LIMITS = {
    "free":       {"claude_calls": 100,   "tool_calls": 200},
    "pro":        {"claude_calls": 2000,  "tool_calls": 5000},
    "enterprise": {"claude_calls": 99999, "tool_calls": 99999},
}


def _billing_period() -> str:
    """Returns current billing period key e.g. '2024-03'"""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


def _redis_key(tenant_id: str, metric: str) -> str:
    """Returns Redis key for a tenant's metric this billing period."""
    return f"usage:{tenant_id}:{_billing_period()}:{metric}"


def _get_tenant_plan(tenant_id: str) -> str:
    """Fetches tenant's current plan from Supabase."""
    result = supabase.table("tenants") \
        .select("plan") \
        .eq("id", tenant_id) \
        .maybe_single() \
        .execute()

    if result.data and result:
        return result.data["plan"]
    return "free"  # default to most restrictive


# ============================================================
# CHECK LIMIT
# Call this before each Claude API call.
# Raises ValueError if the tenant is over their plan limit.
# ============================================================
def check_claude_limit(tenant_id: str):
    plan   = _get_tenant_plan(tenant_id)
    limit  = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])["claude_calls"]
    key    = _redis_key(tenant_id, "claude_calls")

    try:
        current = int(redis_client.get(key) or 0)
    except Exception:
        # Redis unavailable — fall back to Postgres
        current = _get_postgres_count(tenant_id, "claude_calls")

    if current >= limit:
        raise ValueError(
            f"Claude call limit reached for plan '{plan}' ({limit}/month). "
            f"Please upgrade your plan."
        )


# ============================================================
# CHECK TOOL LIMIT
# Call this before each tool execution.
# ============================================================
def check_tool_limit(tenant_id: str):
    plan   = _get_tenant_plan(tenant_id)
    limit  = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])["tool_calls"]
    key    = _redis_key(tenant_id, "tool_calls")

    try:
        current = int(redis_client.get(key) or 0)
    except Exception:
        current = _get_postgres_count(tenant_id, "tool_calls")

    if current >= limit:
        raise ValueError(
            f"Tool call limit reached for plan '{plan}' ({limit}/month). "
            f"Please upgrade your plan."
        )


# ============================================================
# INCREMENT COUNTERS
# Call these after a successful Claude call or tool execution.
# Sets Redis TTL to end of billing month automatically.
# ============================================================
def increment_claude_calls(tenant_id: str):
    key = _redis_key(tenant_id, "claude_calls")
    try:
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expireat(key, _end_of_month_timestamp())
        pipe.execute()
    except Exception as e:
        print(f"[rate_limiter] Redis increment failed: {e}")
    finally:
        _sync_to_postgres(tenant_id, "claude_calls")


def increment_tool_calls(tenant_id: str):
    key = _redis_key(tenant_id, "tool_calls")
    try:
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expireat(key, _end_of_month_timestamp())
        pipe.execute()
    except Exception as e:
        print(f"[rate_limiter] Redis increment failed: {e}")
    finally:
        _sync_to_postgres(tenant_id, "tool_calls")


# ============================================================
# GET USAGE
# Returns current usage stats for a tenant.
# Used by the admin dashboard and billing pages.
# ============================================================
def get_usage(tenant_id: str) -> dict:
    plan = _get_tenant_plan(tenant_id)
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    try:
        claude_key = _redis_key(tenant_id, "claude_calls")
        tool_key   = _redis_key(tenant_id, "tool_calls")
        claude_used = int(redis_client.get(claude_key) or 0)
        tool_used   = int(redis_client.get(tool_key)   or 0)
    except Exception:
        claude_used = _get_postgres_count(tenant_id, "claude_calls")
        tool_used   = _get_postgres_count(tenant_id, "tool_calls")

    return {
        "plan":              plan,
        "billing_period":    _billing_period(),
        "claude_calls": {
            "used":      claude_used,
            "limit":     limits["claude_calls"],
            "remaining": max(0, limits["claude_calls"] - claude_used),
        },
        "tool_calls": {
            "used":      tool_used,
            "limit":     limits["tool_calls"],
            "remaining": max(0, limits["tool_calls"] - tool_used),
        },
    }


# ============================================================
# HELPERS
# ============================================================
def _end_of_month_timestamp() -> int:
    """Returns Unix timestamp for the last second of the current month."""
    from calendar import monthrange
    now = datetime.now(timezone.utc)
    last_day = monthrange(now.year, now.month)[1]
    end = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=0)
    return int(end.timestamp())


def _get_postgres_count(tenant_id: str, metric: str) -> int:
    """Fallback: reads usage count directly from Postgres."""
    period = _billing_period() + "-01"
    try:
        result = supabase.table("tenant_usage") \
            .select(metric) \
            .eq("tenant_id", tenant_id) \
            .eq("billing_period_start", period) \
            .maybe_single() \
            .execute()

        if result and result.data:
            return result.data.get(metric, 0)
        return 0
    except Exception:
        return 0

def _sync_to_postgres(tenant_id: str, metric: str):
    """Syncs current Redis counter to Postgres tenant_usage table."""
    try:
        key     = _redis_key(tenant_id, metric)
        current = int(redis_client.get(key) or 0)
        period  = _billing_period() + "-01"

        supabase.table("tenant_usage").upsert({
            "tenant_id":           tenant_id,
            "billing_period_start": period,
            metric:                current,
        }, on_conflict="tenant_id,billing_period_start").execute()
    except Exception as e:
        print(f"[rate_limiter] Postgres sync failed: {e}")
