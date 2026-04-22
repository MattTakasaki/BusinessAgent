# ============================================================
# chat_router.py
# The /chat endpoint. Accepts user messages and streams
# the agent response back via Server-Sent Events (SSE).
# Mount in main.py: app.include_router(chat_router)
# ============================================================

import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from dependencies import get_current_user
from agent.agent_core import agent_stream
from tools.registry import ToolRegistry

load_dotenv()

chat_router = APIRouter(prefix="/chat", tags=["chat"])
tool_registry = ToolRegistry()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None   # optional — frontend can pass existing session ID


@chat_router.post("/")
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id   = current_user["id"]
    tenant_id = current_user["tenant_id"]

    # Use provided session_id or generate a new one
    session_id = request.session_id or str(uuid.uuid4())

    async def event_generator():
        async for chunk in agent_stream(
            user_message=request.message,
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id,
            tool_registry=tool_registry,
        ):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",        # disables nginx buffering
            "Access-Control-Allow-Origin": "*",
        }
    )
