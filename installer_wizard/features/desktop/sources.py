from datetime import datetime

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
    return {"sunrise": rise.strftime("%H:%M"), "sunset": set_.strftime("%H:%M"), "up": rise <= now < set_,
            "progress": round(progress, 1), "daylight_min": int(span // 60), "place": str(sun.PLACE.get("name", ""))[:60]}


def home_rooms() -> dict | None:
    from features.home_assistant import home
    brief = home.brain.brief()
    rooms = [str(r)[:40] for r in brief.get("occupied", [])][:12]
    return {"rooms": rooms} if rooms and brief.get("status") == "online" else None


def update_ready() -> dict | None:
    up = store.update or {}
    if not up.get("available") or store.phase not in READY_PHASES:
        return None
    return {"local": str(up.get("local_rev", ""))[:10], "remote": str(up.get("target_rev") or up.get("remote_rev", ""))[:10],
            "changes": [str(c)[:120] for c in (up.get("changelog") or [])][:6]}


def components_down() -> dict | None:
    if store.phase not in READY_PHASES:
        return None
    down = [{"label": str(c.get("label", k))[:60], "detail": str(c.get("detail", ""))[:120], "status": c.get("status")}
            for k, c in (store.components or {}).items() if c.get("status") == "down"]
    return {"items": down[:8]} if down else None


def system_monitor() -> dict | None:
    from features.governor.service import governor
    last = governor.last or {}
    if "cpu" not in last or "mem" not in last:
        return None
    return {"cpu": last["cpu"], "ram": last["mem"]}


def system_health() -> dict | None:
    from features.desktop import briefing
    return briefing.resources()[1]


def network_devices() -> dict | None:
    from features.network.explorer import explorer
    online = [d for d in explorer.devices.values() if d.get("online")]
    if not online:
        return None
    return {"items": [{"label": str(explorer.label(d))[:60], "value": str(d.get("ip") or "")[:45]} for d in online[:20]]}


async def weather() -> dict | None:
    from features.chat.skills.weather import weather_skill
    _, ui = await weather_skill("")
    panel = next((p for p in ui.get("panels", []) if p.get("type") == "forecast"), None)
    return panel["data"] if panel else None


SOURCES = {"sun_cycle": sun_cycle, "home_rooms": home_rooms, "update_ready": update_ready, "components_down": components_down}
PROVIDERS = {"system_monitor": system_monitor, "system_health": system_health, "network_devices": network_devices,
             "sun_cycle": sun_cycle, "weather": weather}
