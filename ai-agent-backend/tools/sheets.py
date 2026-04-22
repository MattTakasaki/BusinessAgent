# ============================================================
# tools/sheets.py
# Google Sheets tool adapter — read and write cell data.
# ============================================================

import httpx
from token_service import TokenService

token_service = TokenService()

class SheetsTool:

    async def read(self, tool_input: dict, user_id: str, tenant_id: str) -> dict:
        access_token   = await token_service.get_valid_token(user_id, "google")
        spreadsheet_id = tool_input["spreadsheet_id"]
        range_         = tool_input["range"]

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "range":  data.get("range"),
            "values": data.get("values", []),
        }


    async def write(self, tool_input: dict, user_id: str, tenant_id: str) -> dict:
        access_token   = await token_service.get_valid_token(user_id, "google")
        spreadsheet_id = tool_input["spreadsheet_id"]
        range_         = tool_input["range"]
        values         = tool_input["values"]

        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"valueInputOption": "USER_ENTERED"},
                json={"range": range_, "values": values}
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "updated":       True,
            "updated_range": data.get("updatedRange"),
            "updated_cells": data.get("updatedCells"),
        }
