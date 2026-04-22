# ============================================================
# admin_router.py
# Backend endpoints for the admin dashboard.
# Allows platform owner to read/write per-tenant agent configs.
# Mount in main.py: app.include_router(admin_router)
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import os

load_dotenv()

supabase: Client = create_client(
    os.environ.get("SUPABASE_URL", ""),
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
)

admin_router = APIRouter(prefix="/admin", tags=["admin"])

from dependencies import get_current_user


class BrandingModel(BaseModel):
    primaryColor: str = "#2563eb"
    logoUrl: Optional[str] = None


class AgentConfigModel(BaseModel):
    agent_name: str = "Assistant"
    agent_tone: str = "professional"
    business_context: Optional[str] = None
    custom_instructions: Optional[str] = None
    enabled_tools: List[str] = []
    branding: BrandingModel = BrandingModel()


# ============================================================
# GET /admin/config
# Returns the agent config for the current user's tenant.
# ============================================================
@admin_router.get("/config")
async def get_config(current_user: dict = Depends(get_current_user)):
    try:
        result = supabase.table("agent_configs") \
            .select("*") \
            .eq("tenant_id", current_user["tenant_id"]) \
            .maybe_single() \
            .execute()

        if result and result.data:
            return result.data
    except Exception:
        pass

    return AgentConfigModel()


# ============================================================
# POST /admin/config
# Creates or updates the agent config for the current tenant.
# ============================================================
@admin_router.post("/config")
async def save_config(
    config: AgentConfigModel,
    current_user: dict = Depends(get_current_user)
):
    # Only admins can save config
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    tenant_id = current_user["tenant_id"]

    supabase.table("agent_configs").upsert({
        "tenant_id":           tenant_id,
        "agent_name":          config.agent_name,
        "agent_tone":          config.agent_tone,
        "business_context":    config.business_context,
        "custom_instructions": config.custom_instructions,
        "enabled_tools":       config.enabled_tools,
        "branding":            config.branding.dict(),
    }, on_conflict="tenant_id").execute()

    return {"saved": True}


# ============================================================
# GET /admin/tenants
# Platform owner only — list all tenants.
# Useful for a super-admin view.
# ============================================================
@admin_router.get("/tenants")
async def list_tenants(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    result = supabase.table("tenants") \
        .select("id, name, slug, plan, is_active, created_at") \
        .order("created_at", desc=True) \
        .execute()

    return result.data or []


# ============================================================
# PATCH /admin/tenants/{tenant_id}/plan
# Update a tenant's plan tier.
# ============================================================
class PlanUpdate(BaseModel):
    plan: str  # free | pro | enterprise

@admin_router.patch("/tenants/{tenant_id}/plan")
async def update_tenant_plan(
    tenant_id: str,
    update: PlanUpdate,
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    if update.plan not in ("free", "pro", "enterprise"):
        raise HTTPException(status_code=400, detail="Invalid plan")

    supabase.table("tenants") \
        .update({"plan": update.plan}) \
        .eq("id", tenant_id) \
        .execute()

    return {"updated": True, "tenant_id": tenant_id, "plan": update.plan}
