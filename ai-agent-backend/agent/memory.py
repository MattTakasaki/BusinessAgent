# ============================================================
# agent/memory.py
# Summarized long-term memory system.
#
# How it works:
#   - Every conversation turn is saved to conversation_history
#   - When unarchived turn count > SUMMARIZE_THRESHOLD,
#     a summarization job runs: calls Claude to summarize,
#     saves result to memory_snapshots, marks turns as archived
#   - On each agent call, the latest snapshot is injected
#     into the system prompt as "Conversation Memory"
# ============================================================

import os
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
# Returns the latest memory snapshot summary for a user,
# or None if no snapshot exists yet.
# Injected into the system prompt on every agent call.
# ============================================================
def get_memory_context(user_id: str) -> str | None:
    result = supabase.table("memory_snapshots") \
        .select("summary") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()

    if result.data:
        return result.data[0]["summary"]
    return None


# ============================================================
# MAYBE TRIGGER SUMMARIZATION
# Called after each agent response. Checks if unarchived
# turn count has crossed the threshold. If so, summarizes.
# Runs synchronously for now — can be moved to a background
# task queue (e.g. Celery, ARQ) in production.
# ============================================================
def maybe_trigger_summarization(user_id: str, tenant_id: str, session_id: str):
    # Count unarchived turns for this user
    result = supabase.table("conversation_history") \
        .select("id", count="exact") \
        .eq("user_id", user_id) \
        .eq("is_archived", False) \
        .execute()

    turn_count = result.count or 0

    if turn_count >= SUMMARIZE_THRESHOLD:
        _run_summarization(user_id, tenant_id, turn_count)


# ============================================================
# RUN SUMMARIZATION
# Fetches all unarchived turns, asks Claude to summarize them,
# saves the summary, and marks all turns as archived.
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

    # Format turns for summarization prompt
    conversation_text = "\n".join([
        f"{t['role'].upper()}: {t['content']}"
        for t in turns
        if t.get("content")
    ])

    # Ask Claude to summarize
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"""Summarize the following conversation history concisely.
Focus on:
- Key decisions made
- Important information shared (names, dates, preferences, tasks)
- Actions taken or requested
- Any ongoing tasks or follow-ups needed

Keep the summary under 300 words. Write in third person (e.g. "The user asked...", "The assistant helped...").

Conversation:
{conversation_text}"""
            }]
        )
        summary = response.content[0].text
    except Exception as e:
        print(f"Summarization failed for user {user_id}: {e}")
        return

    # Get latest snapshot version number
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

    print(f"Memory summarized for user {user_id}: {turn_count} turns → version {next_version}")


# ============================================================
# CLEAR MEMORY (admin utility)
# Deletes all snapshots for a user. Useful for testing or
# if a client wants a fresh start.
# ============================================================
def clear_memory(user_id: str):
    supabase.table("memory_snapshots") \
        .delete() \
        .eq("user_id", user_id) \
        .execute()
