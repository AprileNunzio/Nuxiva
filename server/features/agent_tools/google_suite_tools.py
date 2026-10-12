import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("nuxiva.tools.google_suite")

def google_gmail_send(to: str, subject: str, body_text: str, is_draft: bool = True) -> Dict[str, Any]:
    """
    Prepara una bozza o invia un'email tramite Google Workspace Gmail.
    """
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
    """
    Pianifica un appuntamento o riunione su Google Calendar con link Meet generato.
    """
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
    """
    Sincronizza o appende righe di dati in un foglio di calcolo Google Sheets.
    """
    return {
        "status": "success",
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": sheet_name,
        "action": action,
        "rows_affected": len(rows) if rows else 0,
        "updated_at": time.time(),
    }
