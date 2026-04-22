# ============================================================
# dependencies.py
# FastAPI dependency for JWT auth via Supabase.
# ============================================================
from dotenv import load_dotenv
load_dotenv()
import os
from fastapi import HTTPException, Header
from supabase import create_client, Client

supabase: Client = create_client(
    os.environ.get("SUPABASE_URL", ""),
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
)

async def get_current_user(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.removeprefix("Bearer ")

    try:
        user_response = supabase.auth.get_user(token)
        auth_user = user_response.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_row = supabase.table("users") \
        .select("id, tenant_id, role, email") \
        .eq("id", auth_user.id) \
        .maybe_single().execute()

    if not user_row.data:
        raise HTTPException(status_code=404, detail="User not found")

    return user_row.data
