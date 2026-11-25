import time

from fastapi import HTTPException

from access import is_local, session_user
from state import store

from agenti.authz.access_control import account
from agenti.desktop.display_scope import is_host_display
from agenti.desktop.presence_bridge import _require_liveness, _vision_state, face_signal

SUPER_ROLE = "administrator"
OWNER = "owner"


def _admin_session(request) -> bool:
    user = session_user(request) if request.url.scheme == "https" else None
    if not user:
        return False
    record = account(user)
    return record.get("role") == SUPER_ROLE and "*" in (record.get("nodes") or [])


def _owner_in_front(now: float) -> bool:
    from agenti.people.presence import monitor
    presence = getattr(store, "presence", None) or {}
    if _vision_state(presence, monitor.updated_at, now) != "ok":
        return False
    strict = _require_liveness()
    for person in presence.get("people") or []:
        if not isinstance(person, dict) or person.get("role") != OWNER:
            continue
        signal = face_signal(person)
        if signal["person"] and signal["liveness"] != "spoof" and (not strict or signal["liveness"] == "live"):
            return True
    return False


def is_super_admin(request, now: float) -> bool:
    if _admin_session(request):
        return True
    return (is_local(request) or is_host_display(request)) and _owner_in_front(now)


def require_super_admin(request) -> None:
    if not is_super_admin(request, time.time()):
        raise HTTPException(403, "super_admin_required")
