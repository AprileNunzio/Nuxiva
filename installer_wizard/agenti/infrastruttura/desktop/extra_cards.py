import time
from datetime import datetime

AWAY_MIN = 3600
MESH_URGENT = 60


def _ts(entry: dict) -> float:
    try:
        return datetime.fromisoformat(str(entry.get("ts", ""))).timestamp()
    except ValueError:
        return 0.0


def _span(seconds: float) -> str:
    minutes = int(seconds // 60)
    return f"{minutes // 60}h {minutes % 60:02d}m" if minutes >= 60 else f"{minutes}m"


def line(key: str, **params) -> dict:
    return {"key": key, "params": {k: str(v)[:120] for k, v in params.items()}}


def mesh() -> tuple[str, dict, int] | None:
    from agenti.nodes.registry import registry
    nodes = registry.listing()
    if not nodes:
        return None
    online = [n for n in nodes if n.get("online")]
    lines = [line("bf_mesh_online", n=len(online), total=len(nodes))]
    lines += [line("bf_mesh_offline", name=n.get("name", "?")) for n in nodes if not n.get("online")][:4]
    priority = MESH_URGENT if len(online) < len(nodes) else 25
    return "brief", {"title": line("bf_mesh_title"), "lines": lines}, priority


def welcome(events: list, since: float, now: float | None = None, home_names: list[str] | None = None,
            devices: list[dict] | None = None) -> tuple[str, dict, int] | None:
    now = time.time() if now is None else now
    if not since or now - since < AWAY_MIN:
        return None
    recent = [e for e in events if _ts(e) >= since]
    warns = sum(1 for e in recent if e.get("level") == "WARN")
    errors = sum(1 for e in recent if e.get("level") == "ERROR")
    fresh = sum(1 for d in devices or [] if float(d.get("first_seen") or 0) >= since)
    lines = [line("bf_away_for", time=_span(now - since))]
    if errors:
        lines.append(line("bf_away_errors", n=errors))
    if warns:
        lines.append(line("bf_away_alerts", n=warns))
    if fresh:
        lines.append(line("bf_away_devices", n=fresh))
    if home_names:
        lines.append(line("bf_away_people", names=", ".join(home_names[:4])))
    if len(lines) == 1:
        lines.append(line("bf_away_quiet"))
    return "brief", {"title": line("bf_away_title"), "lines": lines}, 72
