from datetime import datetime, timedelta

import psutil

from state import store

READY_PHASES = ("READY", "DEGRADED")


def sun_cycle() -> dict | None:
    from features.automations import sun
    t = sun.times()
    rise, set_ = t.get("sunrise"), t.get("sunset")
    if not rise or not set_:
        return None
    now = datetime.now().astimezone()
    span = (set_ - rise).total_seconds()
    progress = max(0.0, min(100.0, (now - rise).total_seconds() * 100 / span)) if span > 0 else 0.0
    prev = sun.times(rise.date() - timedelta(days=1))
    delta = round((span - (prev["sunset"] - prev["sunrise"]).total_seconds()) / 60, 1) if prev.get("sunrise") and prev.get("sunset") else None
    return {"sunrise": rise.strftime("%H:%M"), "sunset": set_.strftime("%H:%M"), "up": rise <= now < set_,
            "progress": round(progress, 1), "daylight_min": int(span // 60), "place": str(sun.PLACE.get("name", ""))[:60],
            "rise_ts": int(rise.timestamp()), "set_ts": int(set_.timestamp()), "delta_min": delta}


def home_rooms() -> dict | None:
    from features.home_assistant import home
    brief = home.brain.brief()
    rooms = [str(r)[:40] for r in brief.get("occupied", [])][:12]
    return {"rooms": rooms} if rooms and brief.get("status") == "online" else None


def update_ready() -> dict | None:
    up = store.update or {}
    if not up.get("available") or store.phase not in READY_PHASES:
        return None
    log = [str(c)[:160] for c in (up.get("changelog") or [])]
    try:
        from features.update_center.policy import load_policy
        from config import env_get
        policy = load_policy(env_get)
        auto, window = policy.auto_update, policy.window
    except Exception:
        auto, window = None, ""
    return {"local": str(up.get("local_rev", ""))[:10], "remote": str(up.get("target_rev") or up.get("remote_rev", ""))[:10],
            "changes": log[:6], "count": len(log), "auto": auto, "window": window, "checked": str(up.get("last_check") or "")[:40]}


def components_down() -> dict | None:
    if store.phase not in READY_PHASES:
        return None
    from health import CRITICAL
    down = [{"key": str(k)[:40], "label": str(c.get("label", k))[:60], "detail": str(c.get("detail", ""))[:120], "status": c.get("status"),
             "since": c.get("since"), "failures": int(c.get("failures") or 0), "critical": k in CRITICAL}
            for k, c in (store.components or {}).items() if c.get("status") == "down"]
    return {"items": down[:8]} if down else None


def system_monitor() -> dict | None:
    from features.governor.service import governor
    last = governor.last or {}
    if "cpu" not in last or "mem" not in last:
        return None
    return {"cpu": last["cpu"], "ram": last["mem"], "swap": last.get("swap"), "load": last.get("load"), "temp": last.get("temp"),
            "pressure": last.get("pressure"), "high": bool(last.get("high")), "cores": psutil.cpu_count() or 0}


def system_health() -> dict | None:
    from features.desktop import briefing
    return briefing.resources()[1]


def network_devices() -> dict | None:
    from features.network.explorer import explorer
    online = [d for d in explorer.devices.values() if d.get("online")]
    if not online:
        return None
    return {"items": [{"label": str(explorer.label(d))[:60], "value": str(d.get("ip") or "")[:45], "type": str(d.get("type") or "unknown")[:20],
                       "trusted": bool(d.get("trusted")), "room": str(d.get("room") or "")[:40], "since": d.get("first_seen")}
                      for d in online[:20]], "total": len(explorer.devices)}


async def weather() -> dict | None:
    from features.chat.skills.weather import weather_skill
    _, ui = await weather_skill("")
    panel = next((p for p in ui.get("panels", []) if p.get("type") == "forecast"), None)
    return panel["data"] if panel else None


SOURCES = {"sun_cycle": sun_cycle, "home_rooms": home_rooms, "update_ready": update_ready, "components_down": components_down}
PROVIDERS = {"system_monitor": system_monitor, "system_health": system_health, "network_devices": network_devices,
             "sun_cycle": sun_cycle, "weather": weather}
