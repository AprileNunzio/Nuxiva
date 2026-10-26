import asyncio
import math

from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from features.home_assistant import connection_api, control_api, home
from features.home_assistant.automations import api as automations_api
from features.home_assistant.connection import HAError
from state import store

admin_routes = APIRouter()
admin_routes.include_router(automations_api.admin_routes)
admin_routes.include_router(control_api.admin_routes)
admin_routes.include_router(connection_api.admin_routes)


@admin_routes.get("/api/home")
async def admin_home(_: str = Depends(require_admin)):
    return home.brain.overview()


@admin_routes.get("/api/home/devices")
async def admin_home_devices(_: str = Depends(require_admin)):
    return home.brain.device_list()


@admin_routes.get("/api/home/activity")
async def admin_home_activity(hours: int = 24, _: str = Depends(require_admin)):
    return {"activity": home.brain.activity(max(1, min(hours, 24 * 30))), "commands": home.brain.commands()}


@admin_routes.post("/api/home/sync")
async def admin_home_sync(user: str = Depends(require_admin)):
    if not home.brain.online:
        raise HTTPException(409, "Home Assistant non è collegato")
    try:
        await home.brain.sync(f"richiesto da {user}")
    except (HAError, asyncio.TimeoutError) as exc:
        raise HTTPException(502, f"Studio della casa non riuscito: {exc}")
    store.event("INFO", f"Casa ristudiata su richiesta di {user}: {home.brain.summary_line()}", "home")
    return home.brain.overview()


@admin_routes.post("/api/home/test")
async def admin_home_test(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    text = str(body.get("text", "")).strip()[:300]
    if not text:
        raise HTTPException(400, "Scrivi un comando")
    return await home.brain.test(text, bool(body.get("run")))


@admin_routes.put("/api/home/aliases")
async def admin_home_aliases(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    names = body.get("names") or []
    if isinstance(names, str):
        names = names.split(",")
    try:
        home.brain.set_aliases(str(body.get("target", "")), [str(n) for n in names])
    except KeyError:
        raise HTTPException(404, "Stanza o entità sconosciuta")
    return {"ok": True}


@admin_routes.delete("/api/home/learned")
async def admin_home_forget(user: str = Depends(require_admin)):
    home.brain.forget_learned()
    store.event("INFO", f"Frasi della casa imparate dimenticate da {user}", "home")
    return {"ok": True}


@admin_routes.post("/api/home/assist")
async def admin_home_assist(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    text = str(body.get("text", "")).strip()[:300]
    language = str(body.get("language", "it")).strip()
    if not text:
        raise HTTPException(400, "Frase mancante")
    result = await home.brain.ask_assist(text, language)
    return result


@admin_routes.get("/api/home/energy")
async def admin_home_energy(_: str = Depends(require_admin)):
    """Restituisce le letture reali di potenza (W/kW) ed energia (kWh) da Home Assistant."""
    brain = home.brain
    power_sensors, energy_sensors, solar_sensors = [], [], []

    for eid, entity in brain.entities.items():
        if entity.get("domain") != "sensor" or eid not in brain.states:
            continue
        st = brain.states[eid]
        attrs = st.get("attrs") or {}
        raw_unit = str(attrs.get("unit_of_measurement") or "").replace(" ", "")
        unit = raw_unit.lower()
        dev_class = entity.get("device_class") or attrs.get("device_class") or ""
        name = entity.get("name") or eid
        state_str = str(st.get("state", ""))

        try:
            val = float(state_str)
            if not math.isfinite(val) or not brain.online:
                val = None
        except (ValueError, TypeError):
            val = None

        item = {
            "entity_id": eid,
            "name": name,
            "state": val,
            "unit": raw_unit,
            "device_class": dev_class,
            "area_id": entity.get("area_id") or "",
            "raw_state": state_str,
        }

        # Potenza istantanea (W, kW, mW)
        if unit in ("w", "kw", "mw") or dev_class == "power":
            factor = {"W": 1, "kW": 1000, "MW": 1000000, "mW": 0.001}.get(raw_unit)
            power_w = val * factor if val is not None and factor is not None else None
            item["power_w"] = power_w
            is_solar = any(k in eid.lower() or k in name.lower() for k in ("solar", "fotovoltaic", "pv", "inverter"))
            if is_solar:
                solar_sensors.append(item)
            else:
                power_sensors.append(item)

        # Energia cumulativa (Wh, kWh, MWh)
        elif unit in ("wh", "kwh", "mwh") or dev_class == "energy":
            factor = {"Wh": 0.001, "kWh": 1, "MWh": 1000}.get(raw_unit)
            energy_kwh = val * factor if val is not None and factor is not None else None
            item["energy_kwh"] = energy_kwh
            energy_sensors.append(item)

    # No authoritative whole-home/grid meter mapping is configured here.
    # Maxima, name matching and sums of overlapping sensors are not measurements.
    return {
        "power_sensors": sorted(power_sensors, key=lambda s: s.get("power_w") or 0, reverse=True),
        "energy_sensors": energy_sensors,
        "solar_sensors": solar_sensors,
        "summary": {
            "total_power_w": None,
            "total_solar_w": None,
            "net_power_w": None,
        }
    }


@admin_routes.get("/api/home/rooms")
async def admin_home_rooms(_: str = Depends(require_admin)):
    """Restituisce le stanze con i relativi dispositivi, integrando Home Assistant e Places."""
    from features.places.store import store as places_store
    brain = home.brain

    ha_areas = brain.areas
    ha_floors = brain.floors
    places_rooms = places_store.rooms
    places_floors = places_store.floors

    results = []
    # Raggruppa per aree di Home Assistant
    for aid, area in ha_areas.items():
        # Cerca stanza corrispondente in places
        matched_room = next((r for r in places_rooms.values() if r.ha_area == aid or r.name.lower() == area["name"].lower()), None)
        floor_id = (matched_room.floor_id if matched_room else area.get("floor_id")) or ""
        matched_floor = places_floors.get(floor_id) or ha_floors.get(floor_id) or {}
        floor_name = matched_floor.name if hasattr(matched_floor, "name") else matched_floor.get("name", "")

        status = brain.room_status(aid)
        entities = [
            {"entity_id": eid, "name": (brain.entities.get(eid) or {}).get("name", eid), "domain": (brain.entities.get(eid) or {}).get("domain", ""), "state": (brain.states.get(eid) or {}).get("state")}
            for eid in brain.area_entities.get(aid, [])
        ]
        results.append({
            "area_id": aid,
            "room_id": matched_room.id if matched_room else aid,
            "name": area["name"],
            "floor_id": floor_id,
            "floor_name": floor_name,
            "temperature": status.get("temperature"),
            "humidity": status.get("humidity"),
            "occupied": status.get("occupied", False),
            "last_motion": status.get("last_motion"),
            "open": status.get("open", []),
            "entities": entities,
            "entities_count": len(entities),
        })

    return {"rooms": sorted(results, key=lambda r: (r["floor_name"], r["name"]))}


@admin_routes.get("/api/home/custom_sentences")
async def admin_home_custom_sentences(_: str = Depends(require_admin)):
    from features.home_assistant.custom_assist import load_custom_sentences
    s = home.brain.settings()
    return load_custom_sentences(s.get("config_dir", "/config"))

