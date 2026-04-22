# ============================================================
# tools/excel.py
# Microsoft Excel tool adapter via Microsoft Graph API.
# Reads/writes Excel files stored in the user's OneDrive.
# ============================================================

import httpx
from token_service import TokenService

token_service = TokenService()
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

class ExcelTool:

    async def read(self, tool_input: dict, user_id: str, tenant_id: str) -> dict:
        access_token = await token_service.get_valid_token(user_id, "microsoft")
        file_id      = tool_input["file_id"]
        range_       = tool_input["range"]
        sheet_name   = tool_input.get("sheet_name", "Sheet1")

        range_address = f"{sheet_name}!{range_}" if sheet_name else range_

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GRAPH_BASE}/me/drive/items/{file_id}/workbook/worksheets/{sheet_name}/range(address='{range_}')",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "range":  range_address,
            "values": data.get("values", []),
        }


    async def write(self, tool_input: dict, user_id: str, tenant_id: str) -> dict:
        access_token = await token_service.get_valid_token(user_id, "microsoft")
        file_id      = tool_input["file_id"]
        range_       = tool_input["range"]
        values       = tool_input["values"]
        sheet_name   = tool_input.get("sheet_name", "Sheet1")

        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{GRAPH_BASE}/me/drive/items/{file_id}/workbook/worksheets/{sheet_name}/range(address='{range_}')",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"values": values}
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "updated":       True,
            "updated_range": data.get("address"),
        }
