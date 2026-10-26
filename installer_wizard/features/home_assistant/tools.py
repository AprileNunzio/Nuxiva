from features.agent.registry import tool
from features.home_assistant.home import brain

OWNER = "home_assistant"


@tool("ha_get_state", "legge lo stato attuale e gli attributi reali di un'entità di Home Assistant",
      {"entity_id": "identificatore dell'entità (es. light.salotto, sensor.potenza_totale)"},
      agent=OWNER)
def ha_get_state(entity_id: str) -> dict:
    entity = brain.entities.get(entity_id)
    state = brain.states.get(entity_id)
    if not state:
        return {"error": f"Entità {entity_id} non trovata o stato non disponibile"}
    return {
        "entity_id": entity_id,
        "name": (entity or {}).get("name", entity_id),
        "domain": (entity or {}).get("domain", entity_id.split(".")[0]),
        "state": state.get("state"),
        "attributes": state.get("attrs", {}),
        "last_changed": state.get("lc"),
    }


@tool("ha_call_service", "esegue un servizio o comando su Home Assistant (es. accendi luce, imposta temperatura clima, attiva scena)",
      {"domain": "dominio (es. light, switch, climate, scene)",
       "service": "servizio (es. turn_on, turn_off, set_temperature)",
       "entity_id": "id dell'entità o lista separata da virgole (facoltativo)",
       "service_data": "dizionario con parametri del comando (es. {'brightness_pct': 50}) (facoltativo)"},
      confirm=False, agent=OWNER)
async def ha_call_service(domain: str, service: str, entity_id: str = "", service_data: dict | None = None) -> dict:
    eids = [x.strip() for x in entity_id.split(",") if x.strip()] if entity_id else []
    plan = {
        "kind": "command",
        "action": "tool",
        "how": "agente",
        "sensitive": False,
        "calls": [{"domain": domain, "service": service, "entity_ids": eids, "data": service_data or {}}],
        "entities": eids,
    }
    res = await brain.execute(plan, f"{domain}.{service} {entity_id}", "mcp_tool")
    return res


@tool("ha_list_entities", "elenca le entità di Home Assistant filtrate per dominio (light, switch, sensor, climate...) e/o area/stanza",
      {"domain": "filtro per dominio (facoltativo, es. light)", "area_id": "filtro per stanza o area (facoltativo)"},
      agent=OWNER)
def ha_list_entities(domain: str = "", area_id: str = "") -> list[dict]:
    res = []
    for eid, e in brain.entities.items():
        if domain and e.get("domain") != domain:
            continue
        if area_id and e.get("area_id") != area_id:
            continue
        st = brain.states.get(eid) or {}
        res.append({
            "entity_id": eid,
            "name": e.get("name", eid),
            "domain": e.get("domain"),
            "area_id": e.get("area_id"),
            "state": st.get("state"),
            "controllable": bool(e.get("controllable")),
        })
    return res[:100]


@tool("ha_ask_assist", "invia una frase ad Assist di Home Assistant (esegue custom_sentences come /config/custom_sentences/it/energia.yaml e packages come consumi casa)",
      {"text": "frase o domanda da porre (es. 'quanto sta assorbendo tutta la casa?', 'spegni tutto')",
       "language": "lingua della frase (predefinito 'it')"},
      agent=OWNER)
async def ha_ask_assist(text: str, language: str = "it") -> dict:
    return await brain.ask_assist(text, language)


@tool("ha_energy_consumption", "restituisce l'assorbimento totale istantaneo (W), produzione fotovoltaica (W) e consumo cumulativo (kWh) reali della casa",
      {},
      agent=OWNER)
async def ha_energy_consumption() -> dict:
    # 1. Prova prima con Assist nativo se è presente una frase/package dedicato ai consumi
    assist_check = await brain.ask_assist("quanto sta assorbendo tutta la casa", "it")
    speech = assist_check.get("speech", "") if assist_check.get("ok") else ""

    # 2. Raccoglie tutti i sensori di potenza ed energia
    power_sensors = []
    solar_sensors = []
    total_power = 0.0
    total_solar = 0.0

    for eid, entity in brain.entities.items():
        if entity.get("domain") != "sensor" or eid not in brain.states:
            continue
        st = brain.states[eid]
        attrs = st.get("attrs") or {}
        unit = str(attrs.get("unit_of_measurement") or "").lower().replace(" ", "")
        dev_class = entity.get("device_class") or attrs.get("device_class") or ""
        name = entity.get("name") or eid
        try:
            val = float(st.get("state"))
        except (ValueError, TypeError):
            continue

        if unit in ("w", "kw", "mw") or dev_class == "power":
            power_w = val * 1000 if unit == "kw" else val
            is_solar = any(k in eid.lower() or k in name.lower() for k in ("solar", "fotovoltaic", "pv", "inverter"))
            if is_solar:
                solar_sensors.append({"entity_id": eid, "name": name, "power_w": power_w})
                total_solar += power_w
            else:
                power_sensors.append({"entity_id": eid, "name": name, "power_w": power_w})
                if any(k in eid.lower() or k in name.lower() for k in ("totale", "casa", "main", "grid", "generale", "power")):
                    total_power = max(total_power, power_w)

    if total_power == 0.0 and power_sensors:
        total_power = max(s["power_w"] for s in power_sensors)

    return {
        "speech": speech,
        "total_power_w": round(total_power, 1),
        "total_solar_w": round(total_solar, 1),
        "net_power_w": round(total_power - total_solar, 1),
        "sensors": power_sensors[:10],
        "solar": solar_sensors[:5],
    }


@tool("ha_devices_by_room", "restituisce tutti i dispositivi raggruppati per piano e stanza, integrando Home Assistant e Gestione Piani e Stanze (Places)",
      {},
      agent=OWNER)
def ha_devices_by_room() -> dict:
    from features.places.store import store as places_store
    ha_areas = brain.areas
    ha_floors = brain.floors
    places_rooms = places_store.rooms
    places_floors = places_store.floors

    by_room = []
    for aid, area in ha_areas.items():
        matched_room = next((r for r in places_rooms.values() if r.ha_area == aid or r.name.lower() == area["name"].lower()), None)
        floor_id = (matched_room.floor_id if matched_room else area.get("floor_id")) or ""
        matched_floor = places_floors.get(floor_id) or ha_floors.get(floor_id) or {}
        floor_name = matched_floor.name if hasattr(matched_floor, "name") else matched_floor.get("name", "")

        status = brain.room_status(aid)
        devices_in_room = [
            {"entity_id": eid, "name": brain.entities[eid].get("name", eid), "domain": brain.entities[eid].get("domain", "")}
            for eid in brain.area_entities.get(aid, [])
        ]
        by_room.append({
            "room": area["name"],
            "area_id": aid,
            "floor": floor_name,
            "temperature": status.get("temperature"),
            "humidity": status.get("humidity"),
            "occupied": status.get("occupied", False),
            "devices": devices_in_room,
        })
    return {"rooms": by_room}
