# ============================================================
# oauth_router.py
# Handles OAuth2 authorization and callback for Google and Microsoft
# ============================================================

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
import httpx
import os

from token_service import TokenService
from dependencies import get_current_user

oauth_router = APIRouter(prefix="/auth", tags=["oauth"])
token_service = TokenService()

GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI  = os.environ.get("GOOGLE_REDIRECT_URI", "")

GOOGLE_SCOPES = " ".join([
    "openid", "email", "profile",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
])

MICROSOFT_CLIENT_ID     = os.environ.get("MICROSOFT_CLIENT_ID", "")
MICROSOFT_CLIENT_SECRET = os.environ.get("MICROSOFT_CLIENT_SECRET", "")
MICROSOFT_REDIRECT_URI  = os.environ.get("MICROSOFT_REDIRECT_URI", "")
MICROSOFT_TENANT        = "common"

MICROSOFT_SCOPES = " ".join([
    "offline_access", "User.Read",
    "Mail.ReadWrite", "Calendars.ReadWrite", "Files.ReadWrite",
])


@oauth_router.get("/google/connect")
async def google_connect(current_user: dict = Depends(get_current_user)):
    params = {
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         GOOGLE_SCOPES,
        "access_type":   "offline",
        "prompt":        "consent",
        "state":         current_user["id"],
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url)


@oauth_router.get("/google/callback")
async def google_callback(code: str, state: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code":          code,
                "client_id":     GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri":  GOOGLE_REDIRECT_URI,
                "grant_type":    "authorization_code",
            }
        )
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Google token exchange failed")

    tokens = response.json()
    await token_service.store_tokens(
        user_id=state,
        provider="google",
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        expires_in=tokens["expires_in"],
        scope=tokens.get("scope"),
    )
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{frontend_url}/settings?connected=google")


@oauth_router.get("/microsoft/connect")
async def microsoft_connect(current_user: dict = Depends(get_current_user)):
    params = {
        "client_id":     MICROSOFT_CLIENT_ID,
        "redirect_uri":  MICROSOFT_REDIRECT_URI,
        "response_type": "code",
        "scope":         MICROSOFT_SCOPES,
        "response_mode": "query",
        "state":         current_user["id"],
    }
    url = f"https://login.microsoftonline.com/{MICROSOFT_TENANT}/oauth2/v2.0/authorize?" + urlencode(params)
    return RedirectResponse(url)


@oauth_router.get("/microsoft/callback")
async def microsoft_callback(code: str, state: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://login.microsoftonline.com/{MICROSOFT_TENANT}/oauth2/v2.0/token",
            data={
                "code":          code,
                "client_id":     MICROSOFT_CLIENT_ID,
                "client_secret": MICROSOFT_CLIENT_SECRET,
                "redirect_uri":  MICROSOFT_REDIRECT_URI,
                "grant_type":    "authorization_code",
                "scope":         MICROSOFT_SCOPES,
            }
        )
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Microsoft token exchange failed")

    tokens = response.json()
    await token_service.store_tokens(
        user_id=state,
        provider="microsoft",
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        expires_in=tokens["expires_in"],
        scope=tokens.get("scope"),
    )
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{frontend_url}/settings?connected=microsoft")


@oauth_router.get("/status")
async def oauth_status(current_user: dict = Depends(get_current_user)):
    google_connected    = await token_service.has_valid_token(current_user["id"], "google")
    microsoft_connected = await token_service.has_valid_token(current_user["id"], "microsoft")
    return {"google": google_connected, "microsoft": microsoft_connected}


@oauth_router.delete("/disconnect/{provider}")
async def disconnect_provider(provider: str, current_user: dict = Depends(get_current_user)):
    if provider not in ("google", "microsoft"):
        raise HTTPException(status_code=400, detail="Invalid provider")
    await token_service.delete_tokens(current_user["id"], provider)
    return {"disconnected": provider}
