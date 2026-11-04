import hashlib
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class CalendarAttendee(BaseModel):
    email: str
    displayName: Optional[str] = None
    responseStatus: str = "needsAction"
    optional: bool = False

class CalendarRecurrence(BaseModel):
    frequency: str = "DAILY" # DAILY, WEEKLY, MONTHLY, YEARLY
    interval: int = 1
    count: Optional[int] = None
    until: Optional[str] = None

class CalendarEventDetail(BaseModel):
    event_id: str = ""
    summary: str
    description: str = ""
    location: str = ""
    start_time: str
    end_time: str
    time_zone: str = "Europe/Rome"
    attendees: List[CalendarAttendee] = Field(default_factory=list)
    recurrence: Optional[CalendarRecurrence] = None
    meet_link: str = ""
    reminders_minutes: List[int] = Field(default_factory=lambda: [10, 30])

class CalendarTool:
    def __init__(self) -> None:
        self.tool_id = "google_calendar_tool"
        self.name = "Google Calendar Expert"
        self._events_store: Dict[str, CalendarEventDetail] = {}

    def schedule_event(self, event: CalendarEventDetail) -> Dict[str, Any]:
        evt_id = event.event_id or f"cal_{hashlib.sha256((event.summary + event.start_time).encode()).hexdigest()[:14]}"
        event.event_id = evt_id
        if not event.meet_link and len(event.attendees) > 0:
            event.meet_link = f"https://meet.google.com/{evt_id[:3]}-{evt_id[3:7]}-{evt_id[7:10]}"
        self._events_store[evt_id] = event
        return {"status": "success", "event": event.model_dump()}

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        ev = self._events_store.get(event_id)
        return ev.model_dump() if ev else None

    def update_event(self, event_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        if event_id not in self._events_store:
            return {"status": "error", "message": "Evento non trovato"}
        current = self._events_store[event_id]
        updated_data = current.model_dump()
        updated_data.update(updates)
        new_obj = CalendarEventDetail(**updated_data)
        self._events_store[event_id] = new_obj
        return {"status": "success", "event": new_obj.model_dump()}

    def cancel_event(self, event_id: str) -> Dict[str, Any]:
        if event_id in self._events_store:
            del self._events_store[event_id]
            return {"status": "success", "event_id": event_id, "deleted": True}
        return {"status": "error", "message": "Evento non trovato"}

    def list_upcoming_events(self, limit: int = 10) -> Dict[str, Any]:
        evs = list(self._events_store.values())
        return {"status": "success", "count": len(evs), "events": [e.model_dump() for e in evs[:limit]]}

    def check_availability(self, start_time: str, end_time: str) -> Dict[str, Any]:
        conflicts = [
            e.model_dump() for e in self._events_store.values()
            if e.start_time == start_time or (e.start_time <= start_time < e.end_time)
        ]
        return {
            "status": "success",
            "is_busy": len(conflicts) > 0,
            "conflicts_count": len(conflicts),
            "conflicts": conflicts,
        }

calendar_tool = CalendarTool()
