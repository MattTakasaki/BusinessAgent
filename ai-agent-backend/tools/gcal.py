# ============================================================
# tools/gcal.py
# Google Calendar tool adapter — read and create events.
# ============================================================

import httpx
from datetime import datetime, timedelta, timezone
from token_service import TokenService

token_service = TokenService()

class GCalTool:

    async def read(self, tool_input: dict, user_id: str, tenant_id: str) -> dict:
        access_token = await token_service.get_valid_token(user_id, "google")
        max_results  = tool_input.get("max_results", 10)
        days_ahead   = tool_input.get("days_ahead", 7)

        now      = datetime.now(timezone.utc)
        time_max = now + timedelta(days=days_ahead)

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "timeMin":    now.isoformat(),
                    "timeMax":    time_max.isoformat(),
                    "maxResults": max_results,
                    "singleEvents": True,
                    "orderBy":    "startTime",
                }
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])

        events = []
        for item in items:
            start = item.get("start", {})
            end   = item.get("end", {})
            events.append({
                "id":          item.get("id"),
                "title":       item.get("summary", "No title"),
                "start":       start.get("dateTime") or start.get("date"),
                "end":         end.get("dateTime")   or end.get("date"),
                "description": item.get("description", ""),
                "attendees":   [a["email"] for a in item.get("attendees", [])],
                "location":    item.get("location", ""),
            })

        return {"events": events, "count": len(events)}


    async def create(self, tool_input: dict, user_id: str, tenant_id: str) -> dict:
        access_token = await token_service.get_valid_token(user_id, "google")

        event_body = {
            "summary":     tool_input["title"],
            "start":       {"dateTime": tool_input["start_time"], "timeZone": "UTC"},
            "end":         {"dateTime": tool_input["end_time"],   "timeZone": "UTC"},
            "description": tool_input.get("description", ""),
        }

        attendees = tool_input.get("attendees", [])
        if attendees:
            event_body["attendees"] = [{"email": a} for a in attendees]

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers={"Authorization": f"Bearer {access_token}"},
                json=event_body
            )
            resp.raise_for_status()
            created = resp.json()

        return {
            "created":  True,
            "event_id": created.get("id"),
            "title":    created.get("summary"),
            "start":    created.get("start", {}).get("dateTime"),
            "end":      created.get("end",   {}).get("dateTime"),
            "link":     created.get("htmlLink"),
        }
