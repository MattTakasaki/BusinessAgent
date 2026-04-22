# ============================================================
# agent/agent_core.py
# Core agent loop: streams Claude responses via SSE,
# handles tool use blocks, and assembles context from memory.
# ============================================================

import os
import json
import anthropic
from typing import AsyncGenerator
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

supabase: Client = create_client(
    os.environ.get("SUPABASE_URL", ""),
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
)

# ============================================================
# ASSEMBLE SYSTEM PROMPT
# Builds the full system prompt for a tenant's agent by combining:
#   1. Base agent instructions
#   2. Business context + custom instructions from agent_config
#   3. Available tool definitions (passed in from tool registry)
# ============================================================
def build_system_prompt(agent_config: dict) -> str:
    base = """You are a helpful AI business assistant with access to the user's email, calendar, and spreadsheets.
You help users manage their work efficiently by taking actions on their behalf when asked.
Always confirm before sending emails or making calendar changes unless explicitly told otherwise.
Be concise, professional, and proactive in suggesting helpful follow-ups."""

    business_context = ""
    if agent_config.get("business_context"):
        business_context = f"\n\n## About This Business\n{agent_config['business_context']}"

    custom_instructions = ""
    if agent_config.get("custom_instructions"):
        custom_instructions = f"\n\n## Special Instructions\n{agent_config['custom_instructions']}"

    tone = agent_config.get("agent_tone", "professional")
    tone_instruction = f"\n\n## Tone\nCommunicate in a {tone} tone at all times."

    return base + business_context + custom_instructions + tone_instruction


# ============================================================
# LOAD AGENT CONFIG
# Fetches the tenant's agent configuration from the database.
# ============================================================
def load_agent_config(tenant_id: str) -> dict:
    result = supabase.table("agent_configs") \
        .select("*") \
        .eq("tenant_id", tenant_id) \
        .maybe_single() \
        .execute()

    if not result.data:
        # Return sensible defaults if no config exists yet
        return {
            "agent_name": "Assistant",
            "agent_tone": "professional",
            "business_context": None,
            "custom_instructions": None,
            "enabled_tools": ["gmail_read", "gmail_send", "gcal_read", "gcal_create", "sheets_read"],
        }
    return result.data


# ============================================================
# SAVE MESSAGE TO HISTORY
# Persists each turn to conversation_history for memory system.
# ============================================================
def save_message(tenant_id: str, user_id: str, session_id: str, role: str, content: str, tool_calls=None, tool_results=None):
    supabase.table("conversation_history").insert({
        "tenant_id":    tenant_id,
        "user_id":      user_id,
        "session_id":   session_id,
        "role":         role,
        "content":      content,
        "tool_calls":   tool_calls,
        "tool_results": tool_results,
        "is_archived":  False,
    }).execute()


# ============================================================
# LOAD RECENT MESSAGES
# Fetches the last N unarchived messages for short-term context.
# ============================================================
def load_recent_messages(user_id: str, session_id: str, limit: int = 6) -> list:
    result = supabase.table("conversation_history") \
        .select("role, content, tool_calls, tool_results") \
        .eq("user_id", user_id) \
        .eq("session_id", session_id) \
        .eq("is_archived", False) \
        .order("created_at", desc=False) \
        .limit(limit) \
        .execute()

    messages = []
    for row in (result.data or []):
        msg = {"role": row["role"], "content": row["content"]}
        messages.append(msg)
    return messages


# ============================================================
# MAIN AGENT STREAM
# The core function. Called by the /chat endpoint.
# Yields SSE-formatted strings for the frontend to consume.
#
# Flow:
#   1. Load agent config + memory snapshot
#   2. Build message history
#   3. Stream Claude response
#   4. If tool_use block arrives → execute tool → resume stream
#   5. Save all turns to conversation_history
# ============================================================
async def agent_stream(
    user_message: str,
    user_id: str,
    tenant_id: str,
    session_id: str,
    tool_registry,          # ToolRegistry instance (injected from tools/registry.py)
) -> AsyncGenerator[str, None]:

    # Load config and memory
    agent_config  = load_agent_config(tenant_id)
    system_prompt = build_system_prompt(agent_config)

    # Import here to avoid circular imports
    from agent.memory import get_memory_context, maybe_trigger_summarization
    memory_context = get_memory_context(user_id)

    if memory_context:
        system_prompt += f"\n\n## Conversation Memory\n{memory_context}"

    # Load recent messages for short-term context
    recent_messages = load_recent_messages(user_id, session_id)

    # Append the new user message
    messages = recent_messages + [{"role": "user", "content": user_message}]

    # Save user message to DB
    save_message(tenant_id, user_id, session_id, "user", user_message)

    # Get tool definitions for this tenant's enabled tools
    enabled_tools  = agent_config.get("enabled_tools", [])
    tool_definitions = tool_registry.get_tool_definitions(enabled_tools)

    # --------------------------------------------------------
    # STREAMING LOOP
    # Handles multi-turn tool use: Claude may call tools
    # multiple times before producing a final text response.
    # --------------------------------------------------------
    full_response_text = ""
    all_tool_calls     = []

    while True:
        # Stream from Claude
        tool_use_blocks  = []
        current_text     = ""

        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system_prompt,
            messages=messages,
            tools=tool_definitions if tool_definitions else [],
        ) as stream:
            for event in stream:
                # Text delta — forward directly to client
                if hasattr(event, "type"):
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            chunk = event.delta.text
                            current_text += chunk
                            # Yield SSE formatted chunk
                            yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"

                    elif event.type == "content_block_start":
                        if hasattr(event.content_block, "type") and event.content_block.type == "tool_use":
                            tool_use_blocks.append({
                                "id":    event.content_block.id,
                                "name":  event.content_block.name,
                                "input": {}
                            })

                    elif event.type == "content_block_delta":
                        if hasattr(event.delta, "type") and event.delta.type == "input_json_delta":
                            if tool_use_blocks:
                                tool_use_blocks[-1]["input_raw"] = \
                                    tool_use_blocks[-1].get("input_raw", "") + event.delta.partial_json

            # After stream ends, parse tool inputs
            for block in tool_use_blocks:
                if "input_raw" in block:
                    try:
                        block["input"] = json.loads(block["input_raw"])
                    except Exception:
                        block["input"] = {}

        full_response_text += current_text

        # No tool calls — we're done
        if not tool_use_blocks:
            break

        # --------------------------------------------------------
        # TOOL EXECUTION
        # Execute each tool call and collect results
        # --------------------------------------------------------
        tool_results = []
        for tool_call in tool_use_blocks:
            tool_name  = tool_call["name"]
            tool_input = tool_call["input"]
            tool_id    = tool_call["id"]

            # Notify frontend a tool is being used
            yield f"data: {json.dumps({'type': 'tool_use', 'tool': tool_name})}\n\n"

            try:
                result = await tool_registry.execute(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    user_id=user_id,
                    tenant_id=tenant_id,
                )
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": tool_id,
                    "content":     json.dumps(result),
                })
                all_tool_calls.append({"tool": tool_name, "input": tool_input, "result": result})

            except Exception as e:
                error_msg = f"Tool {tool_name} failed: {str(e)}"
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": tool_id,
                    "content":     error_msg,
                    "is_error":    True,
                })
                yield f"data: {json.dumps({'type': 'tool_error', 'tool': tool_name, 'error': error_msg})}\n\n"

        # Add assistant tool use + tool results to messages and loop again
        messages.append({
            "role": "assistant",
            "content": [
                {"type": "text", "text": current_text} if current_text else None,
                *[{"type": "tool_use", "id": t["id"], "name": t["name"], "input": t["input"]}
                  for t in tool_use_blocks]
            ]
        })
        messages.append({"role": "user", "content": tool_results})

    # Save final assistant response to DB
    save_message(
        tenant_id, user_id, session_id,
        role="assistant",
        content=full_response_text,
        tool_calls=all_tool_calls if all_tool_calls else None,
    )

    # Trigger memory summarization if needed (runs async in background)
    maybe_trigger_summarization(user_id, tenant_id, session_id)

    # Signal stream is complete
    yield f"data: {json.dumps({'type': 'done'})}\n\n"
