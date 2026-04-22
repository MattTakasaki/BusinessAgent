# ============================================================
# usage_router.py
# Exposes usage/billing stats to the frontend.
# Mount in main.py: app.include_router(usage_router)
# ============================================================

from fastapi import APIRouter, Depends
from dependencies import get_current_user
from middleware.rate_limiter import get_usage

usage_router = APIRouter(prefix="/usage", tags=["usage"])

@usage_router.get("/")
async def get_tenant_usage(current_user: dict = Depends(get_current_user)):
    return get_usage(current_user["tenant_id"])
