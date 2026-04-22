# ============================================================
# tools/outlook_calendar.py
# Outlook Calendar tool adapter via Microsoft Graph API.
# ============================================================

import httpx
from datetime import datetime, timedelta, timezone
from token_service import TokenService

token_service = TokenService()
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

class OutlookCalendarTool:

    async def read(self, tool_input: dict, user_id: str, tenant_id: str) -> dict:
        access_token = await token_service.get_valid_token(user_id, "microsoft")
        max_results  = tool_input.get("max_results", 10)
        days_ahead   = tool_input.get("days_ahead", 7)

        now      = datetime.now(timezone.utc)
        time_end = now + timedelta(days=days_ahead)

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GRAPH_BASE}/me/calendarView",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "startDateTime": now.isoformat(),
                    "endDateTime":   time_end.isoformat(),
                    "$top":          max_results,
                    "$orderby":      "start/dateTime",
                }
            )
            resp.raise_for_status()
            items = resp.json().get("value", [])

        events = []
        for item in items:
            events.append({
                "id":          item.get("id"),
                "title":       item.get("subject", "No title"),
                "start":       item.get("start", {}).get("dateTime"),
                "end":         item.get("end",   {}).get("dateTime"),
                "description": item.get("bodyPreview", ""),
                "attendees":   [a["emailAddress"]["address"] for a in item.get("attendees", [])],
                "location":    item.get("location", {}).get("displayName", ""),
            })

        return {"events": events, "count": len(events)}


    async def create(self, tool_input: dict, user_id: str, tenant_id: str) -> dict:
        access_token = await token_service.get_valid_token(user_id, "microsoft")

        event_body = {
            "subject": tool_input["title"],
            "start":   {"dateTime": tool_input["start_time"], "timeZone": "UTC"},
            "end":     {"dateTime": tool_input["end_time"],   "timeZone": "UTC"},
            "body":    {"contentType": "Text", "content": tool_input.get("description", "")},
        }

        attendees = tool_input.get("attendees", [])
        if attendees:
            event_body["attendees"] = [
                {"emailAddress": {"address": a}, "type": "required"}
                for a in attendees
            ]

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GRAPH_BASE}/me/events",
                headers={"Authorization": f"Bearer {access_token}"},
                json=event_body
            )
            resp.raise_for_status()
            created = resp.json()

        return {
            "created":  True,
            "event_id": created.get("id"),
            "title":    created.get("subject"),
            "start":    created.get("start", {}).get("dateTime"),
            "end":      created.get("end",   {}).get("dateTime"),
            "link":     created.get("webLink"),
        }
