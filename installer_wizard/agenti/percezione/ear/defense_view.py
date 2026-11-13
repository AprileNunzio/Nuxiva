import math

CONTROLS = frozenset({"defense_view", "defense_state"})
POSTURES = frozenset({"calm", "watch", "alert", "attack"})
MODES = frozenset({"off", "monitor", "protect", "lockdown"})
AUTONOMY = frozenset({"observe", "assist", "autonomous"})
STAGES = frozenset({"recon", "disruption", "intrusion", "interception", "exfiltration"})
LEVELS = frozenset({"low", "medium", "high", "critical"})
KINDS = frozenset({"block", "tarpit", "rate_limit", "honeypot", "quarantine", "sinkhole", "country_block", "warn"})
MAX_ROWS = 12
TEXT = 64


def _text(value, limit: int = TEXT) -> str:
    raw = value if isinstance(value, str) else ""
    return "".join(c for c in raw if c.isprintable())[:limit]


def _number(value, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return low
    return min(high, max(low, float(value)))


def _country(value) -> str:
    raw = value if isinstance(value, str) else ""
    return raw if len(raw) == 2 and raw.isascii() and raw.isalpha() and raw.isupper() else ""


def _pick(value, allowed: frozenset, default: str) -> str:
    return value if isinstance(value, str) and value in allowed else default


def _list(value) -> list:
    return value[:MAX_ROWS] if isinstance(value, list) else []


def _incident(row) -> dict | None:
    if not isinstance(row, dict):
        return None
    kinds = [_text(k, 24) for k in _list(row.get("kinds"))[:4]]
    return {"id": _text(row.get("id"), 48), "kind": _text(row.get("kind"), 24), "kinds": kinds,
            "stage": _pick(row.get("stage"), STAGES, "recon"), "level": _pick(row.get("level"), LEVELS, "low"),
            "country": _country(row.get("country")), "origin": _pick(row.get("origin"), frozenset({"internet", "lan"}), "internet"),
            "src": _text(row.get("src")), "targets": int(_number(row.get("targets"), 0, 100_000)),
            "hosts": [_text(h) for h in _list(row.get("hosts"))[:6]], "last_at": _number(row.get("last_at"), 0, 4e12)}


def _defense(row) -> dict | None:
    if not isinstance(row, dict):
        return None
    return {"kind": _pick(row.get("kind"), KINDS, "warn"), "target": _text(row.get("target")),
            "expires": _number(row.get("expires"), 0, 4e12), "auto": row.get("auto") is True}


def clean_scene(raw) -> dict:
    data = raw if isinstance(raw, dict) else {}
    return {"posture": _pick(data.get("posture"), POSTURES, "calm"), "mode": _pick(data.get("mode"), MODES, "monitor"),
            "autonomy": _pick(data.get("autonomy"), AUTONOMY, "assist"), "trusted": int(_number(data.get("trusted"), 0, 10_000)),
            "internet": int(_number(data.get("internet"), 0, 1_000_000)), "lan": int(_number(data.get("lan"), 0, 1_000_000)),
            "incidents": [i for i in map(_incident, _list(data.get("incidents"))) if i],
            "defenses": [d for d in map(_defense, _list(data.get("defenses"))) if d],
            "at": _number(data.get("at"), 0, 4e12)}


async def defense_control(kind: str, msg: dict, broadcast) -> None:
    if kind == "defense_view":
        opened = msg.get("open") is True
        event = {"type": "defense_view", "open": opened}
        if opened:
            event["scene"] = clean_scene(msg.get("scene"))
        await broadcast(**event)
    elif kind == "defense_state":
        await broadcast(type="defense_state", scene=clean_scene(msg.get("scene")))
