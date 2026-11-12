from __future__ import annotations

import re
import time
from typing import Any, Dict, Optional

IDLE_PHASES = {"READY", "SETUP"}
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _text(value: Any, limit: int) -> str:
    return _CONTROL.sub("", str(value or ""))[:limit].strip()


def view(store: Any, now: Optional[float] = None) -> Optional[Dict[str, Any]]:
    step_id = _text(getattr(store, "current_step", ""), 48)
    if not step_id or getattr(store, "phase", "") in IDLE_PHASES:
        return None
    from steps import STEP_BY_ID

    step = STEP_BY_ID.get(step_id)
    rec = (getattr(store, "steps", {}) or {}).get(step_id) or {}
    last = float(rec.get("last_update") or 0.0)
    return {
        "step": step_id,
        "title": _text(step.title if step else step_id, 80),
        "progress": max(0, min(100, int(rec.get("progress") or 0))),
        "message": _text(rec.get("message"), 200),
        "detail": _text(getattr(store, "detail", ""), 160),
        "silent_for": round(max(0.0, (now or time.time()) - last), 1) if last else None,
    }
