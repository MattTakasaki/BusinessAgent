# ============================================================
# tools/registry.py
# Central registry for all tools. Manages tool definitions
# (sent to Claude) and tool execution (called when Claude
# requests a tool use).
#
# To add a new tool:
#   1. Create the adapter file in tools/
#   2. Import it here
#   3. Add its definition to TOOL_DEFINITIONS
#   4. Add its handler to TOOL_HANDLERS
# ============================================================

from tools.gmail           import GmailTool
from tools.gcal            import GCalTool
from tools.sheets          import SheetsTool
from tools.outlook         import OutlookTool
from tools.outlook_calendar import OutlookCalendarTool
from tools.excel           import ExcelTool

gmail            = GmailTool()
gcal             = GCalTool()
sheets           = SheetsTool()
outlook          = OutlookTool()
outlook_calendar = OutlookCalendarTool()
excel            = ExcelTool()


# ============================================================
# TOOL DEFINITIONS
# These are sent to Claude so it knows what tools are available.
# Claude uses the name + description to decide when to call them.
# ============================================================
TOOL_DEFINITIONS = {

    # ---- GMAIL ----
    "gmail_read": {
        "name": "gmail_read",
        "description": "Read recent emails from the user's Gmail inbox. Use this to check for new messages, find specific emails, or get context before replying.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "Number of emails to retrieve (default 5, max 20)"},
                "query":       {"type": "string",  "description": "Gmail search query e.g. 'from:boss@company.com' or 'subject:invoice'"},
            },
            "required": [],
        }
    },
    "gmail_send": {
        "name": "gmail_send",
        "description": "Send an email from the user's Gmail account.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to":      {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body":    {"type": "string", "description": "Email body (plain text)"},
                "cc":      {"type": "string", "description": "CC email address (optional)"},
            },
            "required": ["to", "subject", "body"],
        }
    },

    # ---- GOOGLE CALENDAR ----
    "gcal_read": {
        "name": "gcal_read",
        "description": "Read upcoming events from the user's Google Calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "Number of events to retrieve (default 10)"},
                "days_ahead":  {"type": "integer", "description": "How many days ahead to look (default 7)"},
            },
            "required": [],
        }
    },
    "gcal_create": {
        "name": "gcal_create",
        "description": "Create a new event on the user's Google Calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":       {"type": "string", "description": "Event title"},
                "start_time":  {"type": "string", "description": "Start time in ISO 8601 format e.g. 2024-03-15T14:00:00"},
                "end_time":    {"type": "string", "description": "End time in ISO 8601 format"},
                "description": {"type": "string", "description": "Event description (optional)"},
                "attendees":   {"type": "array",  "items": {"type": "string"}, "description": "List of attendee email addresses (optional)"},
            },
            "required": ["title", "start_time", "end_time"],
        }
    },

    # ---- GOOGLE SHEETS ----
    "sheets_read": {
        "name": "sheets_read",
        "description": "Read data from a Google Sheet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "The Google Sheets spreadsheet ID (from the URL)"},
                "range":          {"type": "string", "description": "Cell range e.g. 'Sheet1!A1:D10'"},
            },
            "required": ["spreadsheet_id", "range"],
        }
    },
    "sheets_write": {
        "name": "sheets_write",
        "description": "Write or update data in a Google Sheet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "The Google Sheets spreadsheet ID"},
                "range":          {"type": "string", "description": "Cell range to write to e.g. 'Sheet1!A1'"},
                "values":         {"type": "array",  "items": {"type": "array"}, "description": "2D array of values to write"},
            },
            "required": ["spreadsheet_id", "range", "values"],
        }
    },

    # ---- OUTLOOK ----
    "outlook_read": {
        "name": "outlook_read",
        "description": "Read recent emails from the user's Outlook/Microsoft 365 inbox.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "Number of emails to retrieve (default 5, max 20)"},
                "filter":      {"type": "string",  "description": "OData filter query e.g. \"from/emailAddress/address eq 'boss@company.com'\""},
            },
            "required": [],
        }
    },
    "outlook_send": {
        "name": "outlook_send",
        "description": "Send an email from the user's Outlook/Microsoft 365 account.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to":      {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body":    {"type": "string", "description": "Email body (plain text)"},
                "cc":      {"type": "string", "description": "CC email address (optional)"},
            },
            "required": ["to", "subject", "body"],
        }
    },

    # ---- OUTLOOK CALENDAR ----
    "outlook_cal_read": {
        "name": "outlook_cal_read",
        "description": "Read upcoming events from the user's Outlook Calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "Number of events to retrieve (default 10)"},
                "days_ahead":  {"type": "integer", "description": "How many days ahead to look (default 7)"},
            },
            "required": [],
        }
    },
    "outlook_cal_create": {
        "name": "outlook_cal_create",
        "description": "Create a new event on the user's Outlook Calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":       {"type": "string", "description": "Event title"},
                "start_time":  {"type": "string", "description": "Start time in ISO 8601 format"},
                "end_time":    {"type": "string", "description": "End time in ISO 8601 format"},
                "description": {"type": "string", "description": "Event description (optional)"},
                "attendees":   {"type": "array",  "items": {"type": "string"}, "description": "List of attendee email addresses (optional)"},
            },
            "required": ["title", "start_time", "end_time"],
        }
    },

    # ---- EXCEL ----
    "excel_read": {
        "name": "excel_read",
        "description": "Read data from a Microsoft Excel file stored in OneDrive.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id":    {"type": "string", "description": "OneDrive file ID of the Excel file"},
                "sheet_name": {"type": "string", "description": "Name of the worksheet to read"},
                "range":      {"type": "string", "description": "Cell range e.g. 'A1:D10'"},
            },
            "required": ["file_id", "range"],
        }
    },
    "excel_write": {
        "name": "excel_write",
        "description": "Write data to a Microsoft Excel file stored in OneDrive.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id":    {"type": "string", "description": "OneDrive file ID of the Excel file"},
                "sheet_name": {"type": "string", "description": "Name of the worksheet"},
                "range":      {"type": "string", "description": "Cell range to write to"},
                "values":     {"type": "array",  "items": {"type": "array"}, "description": "2D array of values"},
            },
            "required": ["file_id", "range", "values"],
        }
    },
}


# ============================================================
# TOOL HANDLERS
# Maps tool names to their async handler functions.
# ============================================================
TOOL_HANDLERS = {
    "gmail_read":        gmail.read,
    "gmail_send":        gmail.send,
    "gcal_read":         gcal.read,
    "gcal_create":       gcal.create,
    "sheets_read":       sheets.read,
    "sheets_write":      sheets.write,
    "outlook_read":      outlook.read,
    "outlook_send":      outlook.send,
    "outlook_cal_read":  outlook_calendar.read,
    "outlook_cal_create":outlook_calendar.create,
    "excel_read":        excel.read,
    "excel_write":       excel.write,
}


class ToolRegistry:

    def get_tool_definitions(self, enabled_tools: list) -> list:
        """Returns Claude-formatted tool definitions for enabled tools only."""
        return [
            TOOL_DEFINITIONS[name]
            for name in enabled_tools
            if name in TOOL_DEFINITIONS
        ]

    async def execute(self, tool_name: str, tool_input: dict, user_id: str, tenant_id: str) -> dict:
        """Executes a tool by name and returns the result."""
        if tool_name not in TOOL_HANDLERS:
            raise ValueError(f"Unknown tool: {tool_name}")

        handler = TOOL_HANDLERS[tool_name]
        return await handler(tool_input=tool_input, user_id=user_id, tenant_id=tenant_id)
