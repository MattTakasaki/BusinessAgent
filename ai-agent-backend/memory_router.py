# ============================================================
# memory_router.py
# Admin endpoints for inspecting and managing user memory.
# Mount in main.py: app.include_router(memory_router)
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from dotenv import load_dotenv

from dependencies import get_current_user
from agent.memory import (
    get_memory_context,
    get_memory_stats,
    force_summarization,
    clear_memory,
)

load_dotenv()

memory_router = APIRouter(prefix="/memory", tags=["memory"])


# GET /memory/stats — see current memory state for the logged-in user
@memory_router.get("/stats")
async def memory_stats(current_user: dict = Depends(get_current_user)):
    return get_memory_stats(current_user["id"])


# GET /memory/snapshot — see the current memory summary
@memory_router.get("/snapshot")
async def memory_snapshot(current_user: dict = Depends(get_current_user)):
    summary = get_memory_context(current_user["id"])
    if not summary:
        return {"snapshot": None, "message": "No memory snapshot yet"}
    return {"snapshot": summary}


# POST /memory/summarize — force summarization now (admin/testing)
@memory_router.post("/summarize")
async def trigger_summarization(current_user: dict = Depends(get_current_user)):
    result = force_summarization(current_user["id"], current_user["tenant_id"])
    return result


# DELETE /memory/clear — wipe all memory snapshots for this user
@memory_router.delete("/clear")
async def clear_user_memory(current_user: dict = Depends(get_current_user)):
    result = clear_memory(current_user["id"])
    return result
