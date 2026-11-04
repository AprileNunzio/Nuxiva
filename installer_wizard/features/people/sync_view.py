import time

from features.people import connectors
from features.people.sync_board import board
from features.people.vitals import service

MAX_ROWS = 12
DEVICE_STATES = {"streaming": "ok", "connected": "running", "seen": "waiting", "waiting": "waiting", "unsupported": "error"}
DEVICE_KINDS = {"ble": "band", "push": "phone", "phone": "phone"}
ORDER = {"error": 0, "running": 1, "waiting": 2, "ok": 3}


def _row(key: str, state: str, age: float = 0.0, error: str = "", reason: str = "", name: str = "") -> dict:
    return {"key": key, "state": state, "age": round(age, 1), "error": error, "reason": reason, "name": name}


def _google(info: dict, tracked: dict[str, dict]) -> list[dict]:
    if not info.get("linked"):
        return []
    health = [_row("google_health", "error", error="da ricollegare", reason="revoked")] if info.get("health_revoked") else []
    if info.get("revoked"):
        return [_row("google", "error", error="da ricollegare", reason="revoked"), *health]
    rows = [r for k, r in tracked.items() if k.startswith("google") and k != "google_health"]
    return [*(rows or [_row("google", "running")]), *health]


def _other(info: dict) -> list[dict]:
    if not info.get("linked"):
        return []
    status = str(info.get("status") or "")
    if not info.get("available"):
        return [_row(info["id"], "error", reason="unavailable")]
    if status.startswith("errore"):
        return [_row(info["id"], "error", error=status.removeprefix("errore:").strip(), reason="")]
    return [_row(info["id"], "ok")]


def _devices(slug: str, now: float) -> list[dict]:
    rows = []
    for d in service.devices_view(slug, service.current(slug, now), now):
        state = DEVICE_STATES.get(d.get("state", ""))
        if not state:
            continue
        reason = "unsupported" if state == "error" else ""
        rows.append(_row(DEVICE_KINDS.get(d.get("kind", ""), "phone"), state, max(0.0, now - float(d.get("last") or now)),
                         reason=reason, name=str(d.get("label") or "")[:40]))
    return rows


def build(slug: str, now: float | None = None) -> dict | None:
    now = now or time.time()
    tracked = {r["key"]: {**r, "name": ""} for r in board.rows(slug, now)}
    rows: list[dict] = []
    for info in connectors.listing(slug):
        if info.get("id") == "google":
            rows += _google(info, tracked)
        elif info.get("id") != "vitals":
            rows += _other(info)
    if "google_health" in tracked and not any(r["key"] == "google_health" for r in rows):
        rows.append(tracked["google_health"])
    rows += _devices(slug, now)
    if not rows:
        return None
    rows = sorted(rows, key=lambda r: (ORDER.get(r["state"], 9), r["key"], r["name"]))[:MAX_ROWS]
    count = {s: sum(1 for r in rows if r["state"] == s) for s in ORDER}
    phase = "error" if count["error"] else "running" if count["running"] or count["waiting"] else "ok"
    return {"phase": phase, "rows": rows, "total": len(rows), "done": count["ok"], "errors": count["error"]}
