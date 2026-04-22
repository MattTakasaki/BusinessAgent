# ============================================================
# token_service.py
# Encrypted storage, retrieval, and refresh of OAuth tokens.
# ============================================================
from dotenv import load_dotenv
load_dotenv()
import os
import httpx
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet
from supabase import create_client, Client

_key = os.environ.get("TOKEN_ENCRYPTION_KEY", "")
_fernet = Fernet(_key.encode() if _key else Fernet.generate_key())

def encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()

def decrypt(value: str) -> str:
    return _fernet.decrypt(value.encode()).decode()

supabase: Client = create_client(
    os.environ.get("SUPABASE_URL", ""),
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
)


class TokenService:

    async def store_tokens(self, user_id, provider, access_token, refresh_token, expires_in, scope=None):
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        existing = supabase.table("oauth_tokens") \
            .select("refresh_token") \
            .eq("user_id", user_id) \
            .eq("provider", provider) \
            .maybe_single().execute()

        if refresh_token:
            stored_refresh = encrypt(refresh_token)
        elif existing.data:
            stored_refresh = existing.data["refresh_token"]
        else:
            raise ValueError(f"No refresh token available for {provider}")

        supabase.table("oauth_tokens").upsert({
            "user_id":       user_id,
            "provider":      provider,
            "access_token":  encrypt(access_token),
            "refresh_token": stored_refresh,
            "token_scope":   scope,
            "expires_at":    expires_at.isoformat(),
        }, on_conflict="user_id,provider").execute()


    async def get_valid_token(self, user_id: str, provider: str) -> str:
        row = supabase.table("oauth_tokens") \
            .select("*").eq("user_id", user_id).eq("provider", provider) \
            .maybe_single().execute()

        if not row.data and row:
            raise ValueError(f"No {provider} token found for user {user_id}.")

        token_data = row.data
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        needs_refresh = expires_at <= datetime.now(timezone.utc) + timedelta(minutes=5)

        if needs_refresh:
            return await self._refresh_token(user_id, provider, token_data)
        return decrypt(token_data["access_token"])


    async def _refresh_token(self, user_id, provider, token_data) -> str:
        refresh_token = decrypt(token_data["refresh_token"])
        if provider == "google":
            new_tokens = await self._refresh_google(refresh_token)
        elif provider == "microsoft":
            new_tokens = await self._refresh_microsoft(refresh_token)
        else:
            raise ValueError(f"Unknown provider: {provider}")

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=new_tokens["expires_in"])
        supabase.table("oauth_tokens").update({
            "access_token": encrypt(new_tokens["access_token"]),
            "expires_at":   expires_at.isoformat(),
        }).eq("user_id", user_id).eq("provider", provider).execute()
        return new_tokens["access_token"]


    async def _refresh_google(self, refresh_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.post("https://oauth2.googleapis.com/token", data={
                "client_id":     os.environ.get("GOOGLE_CLIENT_ID", ""),
                "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
                "refresh_token": refresh_token,
                "grant_type":    "refresh_token",
            })
        if r.status_code != 200:
            raise ValueError(f"Google token refresh failed: {r.text}")
        return r.json()


    async def _refresh_microsoft(self, refresh_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token", data={
                "client_id":     os.environ.get("MICROSOFT_CLIENT_ID", ""),
                "client_secret": os.environ.get("MICROSOFT_CLIENT_SECRET", ""),
                "refresh_token": refresh_token,
                "grant_type":    "refresh_token",
                "scope":         "offline_access Mail.ReadWrite Calendars.ReadWrite Files.ReadWrite",
            })
        if r.status_code != 200:
            raise ValueError(f"Microsoft token refresh failed: {r.text}")
        return r.json()


    async def has_valid_token(self, user_id: str, provider: str) -> bool:
        try:
            await self.get_valid_token(user_id, provider)
            return True
        except ValueError:
            return False


    async def delete_tokens(self, user_id: str, provider: str) -> None:
        supabase.table("oauth_tokens") \
            .delete().eq("user_id", user_id).eq("provider", provider).execute()
