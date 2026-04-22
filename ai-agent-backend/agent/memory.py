# ============================================================
# agent/memory.py
# Summarized long-term memory system.
#
# How it works:
#   - Every turn is saved to conversation_history
#   - When unarchived turn count > SUMMARIZE_THRESHOLD,
#     a background summarization job runs:
#       → fetches all unarchived turns
#       → calls Claude to summarize them
#       → saves result to memory_snapshots
#       → marks turns as archived
#   - On each agent call, the latest snapshot is injected
#     into the system prompt as long-term context
# ============================================================

import os
import asyncio
import anthropic
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

supabase: Client = create_client(
    os.environ.get("SUPABASE_URL", ""),
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
)

SUMMARIZE_THRESHOLD = 20  # summarize after this many unarchived turns


# ============================================================
# GET MEMORY CONTEXT
# Returns the latest snapshot summary for a user.
# Injected into the system prompt on every agent call.
# ============================================================
def get_memory_context(user_id: str) -> str | None:
    result = supabase.table("memory_snapshots") \
        .select("summary, version, created_at") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()

    if result.data:
        return result.data[0]["summary"]
    return None


# ============================================================
# GET MEMORY STATS
# Returns stats about a user's memory — useful for debugging
# and for the admin dashboard.
# ============================================================
def get_memory_stats(user_id: str) -> dict:
    # Count unarchived turns
    unarchived = supabase.table("conversation_history") \
        .select("id", count="exact") \
        .eq("user_id", user_id) \
        .eq("is_archived", False) \
        .execute()

    # Count total turns
    total = supabase.table("conversation_history") \
        .select("id", count="exact") \
        .eq("user_id", user_id) \
        .execute()

    # Get latest snapshot info
    snapshot = supabase.table("memory_snapshots") \
        .select("version, created_at, turn_count") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()

    return {
        "unarchived_turns":    unarchived.count or 0,
        "total_turns":         total.count or 0,
        "summarize_threshold": SUMMARIZE_THRESHOLD,
        "turns_until_summary": max(0, SUMMARIZE_THRESHOLD - (unarchived.count or 0)),
        "latest_snapshot":     snapshot.data[0] if snapshot.data else None,
    }


# ============================================================
# MAYBE TRIGGER SUMMARIZATION
# Called after each agent response via asyncio background task.
# Non-blocking — the response stream completes before this runs.
# ============================================================
def maybe_trigger_summarization(user_id: str, tenant_id: str, session_id: str):
    result = supabase.table("conversation_history") \
        .select("id", count="exact") \
        .eq("user_id", user_id) \
        .eq("is_archived", False) \
        .execute()

    turn_count = result.count or 0

    if turn_count >= SUMMARIZE_THRESHOLD:
        # Run in background so it doesn't block the response
        asyncio.create_task(_run_summarization_async(user_id, tenant_id, turn_count))


# ============================================================
# RUN SUMMARIZATION (async wrapper)
# ============================================================
async def _run_summarization_async(user_id: str, tenant_id: str, turn_count: int):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_summarization, user_id, tenant_id, turn_count)


# ============================================================
# RUN SUMMARIZATION (core logic)
# Fetches unarchived turns, summarizes with Claude,
# saves snapshot, marks turns archived.
# ============================================================
def _run_summarization(user_id: str, tenant_id: str, turn_count: int):
    # Fetch all unarchived turns
    result = supabase.table("conversation_history") \
        .select("id, role, content") \
        .eq("user_id", user_id) \
        .eq("is_archived", False) \
        .order("created_at", desc=False) \
        .execute()

    if not result.data:
        return

    turns = result.data

    # Format turns for summarization
    conversation_text = "\n".join([
        f"{t['role'].upper()}: {t['content']}"
        for t in turns
        if t.get("content")
    ])

    # Call Claude to summarize
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"""Summarize the following business assistant conversation concisely.
Focus on:
- Key decisions made or confirmed
- Important facts shared (names, dates, deadlines, preferences)
- Tasks completed or requested
- Any ongoing items or follow-ups still needed

Keep the summary under 300 words.
Write in third person (e.g. "The user requested...", "The assistant completed...").

Conversation:
{conversation_text}"""
            }]
        )
        summary = response.content[0].text
    except Exception as e:
        print(f"[memory] Summarization failed for user {user_id}: {e}")
        return

    # Get next version number
    latest = supabase.table("memory_snapshots") \
        .select("version") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()

    next_version = (latest.data[0]["version"] + 1) if latest.data else 1

    # Save new snapshot
    supabase.table("memory_snapshots").insert({
        "tenant_id":  tenant_id,
        "user_id":    user_id,
        "summary":    summary,
        "turn_count": turn_count,
        "version":    next_version,
    }).execute()

    # Mark all summarized turns as archived
    turn_ids = [t["id"] for t in turns]
    supabase.table("conversation_history") \
        .update({"is_archived": True}) \
        .in_("id", turn_ids) \
        .execute()

    print(f"[memory] Summarized {turn_count} turns for user {user_id} → snapshot v{next_version}")


# ============================================================
# FORCE SUMMARIZATION
# Admin utility — manually trigger summarization for a user
# regardless of threshold. Useful for testing.
# ============================================================
def force_summarization(user_id: str, tenant_id: str):
    result = supabase.table("conversation_history") \
        .select("id", count="exact") \
        .eq("user_id", user_id) \
        .eq("is_archived", False) \
        .execute()

    turn_count = result.count or 0
    if turn_count == 0:
        return {"message": "No unarchived turns to summarize"}

    _run_summarization(user_id, tenant_id, turn_count)
    return {"message": f"Summarized {turn_count} turns"}


# ============================================================
# CLEAR MEMORY
# Admin utility — deletes all snapshots for a user.
# ============================================================
def clear_memory(user_id: str) -> dict:
    supabase.table("memory_snapshots") \
        .delete() \
        .eq("user_id", user_id) \
        .execute()
    return {"message": "Memory cleared"}
