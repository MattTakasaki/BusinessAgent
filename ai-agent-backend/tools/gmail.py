# ============================================================
# tools/gmail.py
# Gmail tool adapter — read and send emails via Gmail API.
# ============================================================

import base64
import httpx
from email.mime.text import MIMEText
from token_service import TokenService

token_service = TokenService()

class GmailTool:

    async def read(self, tool_input: dict, user_id: str, tenant_id: str) -> dict:
        access_token = await token_service.get_valid_token(user_id, "google")
        max_results  = tool_input.get("max_results", 5)
        query        = tool_input.get("query", "")

        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            # List messages
            params = {"maxResults": max_results, "q": query}
            list_resp = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers=headers, params=params
            )
            list_resp.raise_for_status()
            messages_list = list_resp.json().get("messages", [])

            # Fetch each message
            emails = []
            for msg in messages_list[:max_results]:
                msg_resp = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}",
                    headers=headers,
                    params={"format": "metadata", "metadataHeaders": ["From", "To", "Subject", "Date"]}
                )
                msg_resp.raise_for_status()
                msg_data = msg_resp.json()

                headers_list = msg_data.get("payload", {}).get("headers", [])
                headers_dict = {h["name"]: h["value"] for h in headers_list}

                emails.append({
                    "id":      msg["id"],
                    "from":    headers_dict.get("From", ""),
                    "to":      headers_dict.get("To", ""),
                    "subject": headers_dict.get("Subject", ""),
                    "date":    headers_dict.get("Date", ""),
                    "snippet": msg_data.get("snippet", ""),
                })

        return {"emails": emails, "count": len(emails)}


    async def send(self, tool_input: dict, user_id: str, tenant_id: str) -> dict:
        access_token = await token_service.get_valid_token(user_id, "google")

        to      = tool_input["to"]
        subject = tool_input["subject"]
        body    = tool_input["body"]
        cc      = tool_input.get("cc", "")

        # Build MIME message
        mime = MIMEText(body)
        mime["to"]      = to
        mime["subject"] = subject
        if cc:
            mime["cc"] = cc

        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"raw": raw}
            )
            resp.raise_for_status()

        return {"sent": True, "to": to, "subject": subject}
