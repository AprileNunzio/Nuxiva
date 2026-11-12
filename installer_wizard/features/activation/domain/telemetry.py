from __future__ import annotations

import re
from dataclasses import dataclass

PCT_RE = re.compile(r"(\d{1,3})%")
SPEED_RE = re.compile(r"(\d+(?:\.\d+)?\s*(?:[kKMGT]?B/s|[kKMGT]?iB/s))", re.IGNORECASE)


@dataclass(frozen=True)
class TelemetrySnapshot:
    progress: float = 0.0
    speed: str = ""
    detail: str = ""
    message: str = ""
    elapsed: float = 0.0
    eta: float = 0.0

    def to_dict(self) -> dict:
        return {
            "progress": round(self.progress, 1),
            "speed": self.speed,
            "detail": self.detail,
            "message": self.message,
            "elapsed": round(self.elapsed, 1),
            "eta": round(self.eta, 1),
        }


class TelemetryParser:
    @staticmethod
    def parse_line(line: str) -> dict[str, object]:
        line = line.strip()
        data: dict[str, object] = {}
        if not line:
            return data
        if line.startswith("@@PROGRESS "):
            parts = line.split(" ", 2)
            try:
                data["progress"] = max(0.0, min(100.0, float(parts[1])))
            except (IndexError, ValueError):
                pass
            if len(parts) > 2:
                data["message"] = parts[2][:200]
        elif line.startswith("@@SPEED "):
            data["speed"] = line[8:].strip()[:32]
        elif line.startswith("@@DETAIL "):
            dt = line[9:].strip()
            data["detail"] = dt[:200]
            sm = SPEED_RE.search(dt)
            if sm:
                data["speed"] = sm.group(1)
        else:
            pm = PCT_RE.search(line)
            if pm:
                try:
                    data["progress"] = max(0.0, min(100.0, float(pm.group(1))))
                except ValueError:
                    pass
            sm = SPEED_RE.search(line)
            if sm:
                data["speed"] = sm.group(1)
        return data
