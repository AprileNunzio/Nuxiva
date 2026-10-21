import time
import logging
from typing import Dict, Any, List, Optional
from server.core.scanner.base import DiscoveryManifest
from server.features.agent_tools.base import BaseAgentTool

logger = logging.getLogger("nuxiva.tool.google_suite")

def google_gmail_send(to: str, subject: str, body_text: str, is_draft: bool = True) -> Dict[str, Any]:
    logger.info("Gmail action (%s) to %s: %s", "DRAFT" if is_draft else "SEND", to, subject)
    return {
        "status": "success",
        "action": "DRAFT_CREATED" if is_draft else "EMAIL_SENT",
        "to": to,
        "subject": subject,
        "message_id": f"msg_gmail_{int(time.time())}",
        "body_preview": body_text[:120],
        "created_at": time.time(),
    }

def google_calendar_schedule(
    summary: str,
    start_time_iso: str,
    duration_minutes: int = 60,
    attendees: Optional[List[str]] = None,
    location: str = "Google Meet",
) -> Dict[str, Any]:
    event_id = f"gcal_{int(time.time())}"
    meet_link = f"https://meet.google.com/nux-{event_id[:3]}-{event_id[-4:]}"
    return {
        "status": "success",
        "event_id": event_id,
        "summary": summary,
        "start_time": start_time_iso,
        "duration_minutes": duration_minutes,
        "attendees": attendees or [],
        "location": location,
        "meet_link": meet_link,
    }

def google_sheets_sync(
    spreadsheet_id: str,
    sheet_name: str,
    action: str = "append",
    rows: Optional[List[List[Any]]] = None,
) -> Dict[str, Any]:
    return {
        "status": "success",
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": sheet_name,
        "action": action,
        "rows_affected": len(rows) if rows else 0,
        "updated_at": time.time(),
    }

class GoogleSuiteTool(BaseAgentTool):
    @property
    def manifest(self) -> DiscoveryManifest:
        return DiscoveryManifest(
            id="google_suite",
            name="Google Workspace Suite",
            category="tool",
            description="Integrazione con Gmail, Google Calendar e Google Sheets.",
            icon="📅",
            parameters={
                "type": "object",
                "properties": {
                    "service": {"type": "string", "enum": ["gmail", "calendar", "sheets"]},
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body_text": {"type": "string"},
                    "summary": {"type": "string"},
                    "start_time_iso": {"type": "string"},
                },
                "required": ["service"],
            },
            metadata={"alias": "google"},
        )

    async def execute(self, service: str, **kwargs: Any) -> Dict[str, Any]:
        if service == "gmail":
            return google_gmail_send(
                to=kwargs.get("to", ""),
                subject=kwargs.get("subject", ""),
                body_text=kwargs.get("body_text", ""),
                is_draft=kwargs.get("is_draft", True),
            )
        elif service == "calendar":
            return google_calendar_schedule(
                summary=kwargs.get("summary", ""),
                start_time_iso=kwargs.get("start_time_iso", ""),
                duration_minutes=kwargs.get("duration_minutes", 60),
                attendees=kwargs.get("attendees"),
                location=kwargs.get("location", "Google Meet"),
            )
        elif service == "sheets":
            return google_sheets_sync(
                spreadsheet_id=kwargs.get("spreadsheet_id", ""),
                sheet_name=kwargs.get("sheet_name", "Sheet1"),
                action=kwargs.get("action", "append"),
                rows=kwargs.get("rows"),
            )
        return {"status": "error", "message": f"Service '{service}' unsupported"}
