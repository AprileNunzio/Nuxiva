from __future__ import annotations

import re
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

from . import estimate, parse

MAX_SEGMENTS = 12
FORGET_AFTER = 1800.0
_STEP = re.compile(r"^[a-z][a-z0-9_]{1,47}$")


class BuildLive:
    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self.current: Optional[Dict[str, Any]] = None
        self.segments: Deque[Dict[str, Any]] = deque(maxlen=MAX_SEGMENTS)
        self.units: Deque[float] = deque(maxlen=estimate.MAX_UNITS)

    def _begin(self, step: str, event: Dict[str, Any], now: float) -> Dict[str, Any]:
        if self.segments and now - self.segments[-1]["finished"] > FORGET_AFTER:
            self.segments.clear()
        self.units.clear()
        self.current = {"step": step, "pkg": event["pkg"], "status": "running", "n": 0, "total": event["total"],
                        "crate": None, "started": now, "finished": None, "last_unit": None, "last_beat": now}
        return self.current

    def _close(self, cur: Dict[str, Any], status: str, now: float) -> None:
        cur.update(status=status, finished=now)
        self.segments.append({"pkg": cur["pkg"], "status": status, "n": cur["n"], "total": cur["total"],
                              "started": cur["started"], "finished": now})

    def feed(self, step: str, raw: str) -> bool:
        event = parse.parse(raw)
        if event is None or not _STEP.match(step or ""):
            return False
        now = self._clock()
        cur = self.current
        if event["event"] == "start" or cur is None or cur["pkg"] != event["pkg"] or cur["status"] != "running":
            if cur is not None and cur["status"] == "running":
                self._close(cur, "failed", now)
            cur = self._begin(step, event, now)
        cur["last_beat"] = now
        if event["total"] > 0:
            cur["total"] = event["total"]
        if event["event"] == "unit" and event["n"] > cur["n"]:
            cur["n"] = event["n"]
            cur["last_unit"] = now
            self.units.append(now - cur["started"])
        elif event["event"] == "beat":
            cur["n"] = max(cur["n"], event["n"])
        if event["crate"] and event["event"] in ("unit", "beat"):
            cur["crate"] = event["crate"]
        if event["event"] in ("done", "fail"):
            self._close(cur, "done" if event["event"] == "done" else "failed", now)
        return True

    def _segments(self) -> List[Dict[str, Any]]:
        return [{"pkg": s["pkg"], "status": s["status"], "n": s["n"], "total": s["total"],
                 "seconds": round(s["finished"] - s["started"], 1)} for s in self.segments]

    def public(self) -> Optional[Dict[str, Any]]:
        now = self._clock()
        cur = self.current
        last = (cur["finished"] or cur["last_beat"]) if cur else None
        if cur is None or (last is not None and now - last > FORGET_AFTER):
            return None
        view: Dict[str, Any] = {"now": round(now, 3), "segments": self._segments(), "current": None}
        if cur["status"] == "running":
            elapsed = now - cur["started"]
            view["current"] = {
                "step": cur["step"], "pkg": cur["pkg"], "n": cur["n"], "total": cur["total"], "crate": cur["crate"],
                "started": round(cur["started"], 3), "last_unit": round(cur["last_unit"], 3) if cur["last_unit"] else None,
                "last_beat": round(cur["last_beat"], 3),
                "estimate": estimate.estimate(cur["n"], cur["total"], elapsed, list(self.units)),
            }
        return view


live = BuildLive()
