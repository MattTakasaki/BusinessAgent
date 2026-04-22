# ============================================================
# tools/outlook.py
# Outlook/Microsoft 365 email tool adapter via Microsoft Graph API.
# ============================================================

import httpx
from token_service import TokenService

token_service = TokenService()
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

class OutlookTool:

    async def read(self, tool_input: dict, user_id: str, tenant_id: str) -> dict:
        access_token = await token_service.get_valid_token(user_id, "microsoft")
        max_results  = tool_input.get("max_results", 5)
        filter_query = tool_input.get("filter", "")

        params = {"$top": max_results, "$orderby": "receivedDateTime desc"}
        if filter_query:
            params["$filter"] = filter_query

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GRAPH_BASE}/me/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params
            )
            resp.raise_for_status()
            messages = resp.json().get("value", [])

        emails = []
        for msg in messages:
            emails.append({
                "id":       msg.get("id"),
                "from":     msg.get("from", {}).get("emailAddress", {}).get("address", ""),
                "subject":  msg.get("subject", ""),
                "date":     msg.get("receivedDateTime", ""),
                "snippet":  msg.get("bodyPreview", ""),
                "is_read":  msg.get("isRead", False),
            })

        return {"emails": emails, "count": len(emails)}


    async def send(self, tool_input: dict, user_id: str, tenant_id: str) -> dict:
        access_token = await token_service.get_valid_token(user_id, "microsoft")

        to      = tool_input["to"]
        subject = tool_input["subject"]
        body    = tool_input["body"]
        cc      = tool_input.get("cc", "")

        message = {
            "subject": subject,
            "body":    {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to}}],
        }
        if cc:
            message["ccRecipients"] = [{"emailAddress": {"address": cc}}]

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GRAPH_BASE}/me/sendMail",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"message": message}
            )
            resp.raise_for_status()

        return {"sent": True, "to": to, "subject": subject}
