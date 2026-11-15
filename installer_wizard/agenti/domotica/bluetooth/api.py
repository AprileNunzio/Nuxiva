import json
import logging
import time

from access import NO_CACHE, require_admin, require_display
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from state import store as state_store

from agenti.bluetooth import adapter, schema, store
from agenti.bluetooth.service import gamepads, service
from agenti.bluetooth.text import translate

log = logging.getLogger("nuxiva.bluetooth")
admin_routes = APIRouter()
public_routes = APIRouter()
BODY_LIMIT = 8192
ACTIONS = {"pair": adapter.pair, "connect": adapter.connect, "disconnect": adapter.disconnect,
           "forget": adapter.forget, "trust": adapter.trust, "untrust": adapter.untrust}


def _visible(dev: dict, scanning: bool) -> bool:
    now = time.time()
    recent = (now - dev.get("last_seen", 0)) < 300
    return dev["paired"] or dev["connected"] or (dev["rssi"] is not None) or scanning or recent


def _view(state: dict, notice: str = "") -> dict:
    data = store.load()
    scanning = service.scanning() or bool(state["controller"].get("discovering"))
    devices = [{**d, "settings": store.settings(data, d["mac"])} for d in state["devices"] if _visible(d, scanning)]
    routing = state.get("routing") or {}
    return {"enabled": service.enabled(), "scanning": scanning, "controller": state["controller"], "devices": devices,
            "routing": {"output": routing.get("output"), "input": routing.get("input")},
            "prefs": {k: data[k] for k in (*store.ORDERS, *store.GLOBALS)}, "schema": schema.public(),
            "notice": notice}


async def _body(request: Request) -> object:
    raw = await request.body()
    if len(raw) > BODY_LIMIT:
        raise HTTPException(413, "bluetooth_body_too_large")
    try:
        return json.loads(raw or b"null")
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(400, "bluetooth_invalid_body") from exc


def _ready() -> None:
    if not service.state["controller"].get("installed") or not service.state["controller"].get("present"):
        raise HTTPException(409, "bluetooth_adapter_not_ready")


def _mac(mac: str) -> str:
    try:
        return adapter.valid_mac(mac)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@admin_routes.get("/api/bluetooth")
async def bluetooth_state(_: str = Depends(require_admin)):
    return JSONResponse(_view(await service.current()), headers=NO_CACHE)


@admin_routes.post("/api/bluetooth/scan")
async def bluetooth_scan(_: str = Depends(require_admin)):
    _ready()
    return {"ok": True, "seconds": service.start_scan()}


@admin_routes.post("/api/bluetooth/power")
async def bluetooth_power(request: Request, user: str = Depends(require_admin)):
    body = await _body(request)
    if not isinstance(body, dict) or not isinstance(body.get("on"), bool):
        raise HTTPException(400, "bluetooth_invalid_body")
    _ready()
    try:
        await adapter.power(body["on"])
    except adapter.BluetoothError as exc:
        raise HTTPException(502, "bluetooth_adapter_unresponsive") from exc
    state_store.event("INFO", translate("event_power_on" if body["on"] else "event_power_off", user=user), "bluetooth")
    return _view(await service.refresh())


@admin_routes.post("/api/bluetooth/devices/{mac}/{action}")
async def bluetooth_action(mac: str, action: str, request: Request, user: str = Depends(require_admin)):
    if action not in ACTIONS:
        raise HTTPException(404, "bluetooth_unknown_action")
    mac = _mac(mac)
    _ready()
    person_slug = ""
    try:
        raw = await request.body()
        if raw:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                person_slug = str(parsed.get("person_slug") or "").strip()
    except Exception:
        pass
    try:
        await ACTIONS[action](mac)
    except adapter.BluetoothError as exc:
        err_str = str(exc).strip()
        explanation = err_str
        if "org.bluez.Error.Failed" in err_str:
            explanation = f"{err_str} (Dispositivo non raggiungibile o ha rifiutato la connessione. Verifica che sia visibile e vicino)"
        elif "org.bluez.Error.InProgress" in err_str:
            explanation = "Operazione Bluetooth già in corso. Attendi qualche secondo e riprova."
        elif "org.bluez.Error.NotReady" in err_str:
            explanation = "Adattatore Bluetooth non pronto o occupato. Riprova."
        elif "timeout" in err_str.lower():
            explanation = "Tempo scaduto durante il tentativo di connessione con il dispositivo."
        raise HTTPException(502, detail={"code": f"bluetooth_{action}_failed", "message": explanation}) from exc
    notice = ""
    if action == "pair":
        try:
            await adapter.connect(mac)
        except adapter.BluetoothError:
            notice = "bluetooth_paired_not_connected"
    state = await service.refresh()
    dev = next((d for d in state["devices"] if d["mac"] == mac), None)
    if action == "forget":
        store.forget(mac)
    elif dev and action in ("pair", "connect"):
        store.remember(mac, dev["name"], dev["capabilities"])
        if person_slug:
            store.update_device(mac, {"person_slug": person_slug, "is_personal": True})
            try:
                from agenti.medico.vitals.book import book
                from agenti.percezione.people import service as people_service
                if people_service.people.get(person_slug):
                    kind_str = "band" if dev and dev.get("kind") == "wearable" else "sensor"
                    name_str = dev.get("name", "Dispositivo")
                    book.add(person_slug, kind_str, name_str, mac)
                    state_store.event("INFO", f"Dispositivo '{name_str}' collegato ai parametri vitali di {person_slug}", "bluetooth")
            except Exception as exc:
                log.warning("Collegamento a libro parametri vitali: %s", exc)
    state_store.event("INFO", translate("event_action", action=action, name=dev["name"] if dev else mac, user=user),
                      "bluetooth")
    return _view(await service.refresh(), notice)


@admin_routes.post("/api/bluetooth/reset")
async def bluetooth_reset(_: str = Depends(require_admin)):
    _ready()
    await adapter.reset_adapter()
    return _view(await service.refresh())



@admin_routes.put("/api/bluetooth/devices/{mac}/settings")
async def bluetooth_device_settings(mac: str, request: Request, user: str = Depends(require_admin)):
    mac = _mac(mac)
    body = await _body(request)
    try:
        store.update_device(mac, body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    state = await service.refresh()
    dev = next((d for d in state["devices"] if d["mac"] == mac), None)
    state_store.event("INFO", translate("event_settings", name=dev["name"] if dev else mac, user=user), "bluetooth")
    return _view(state)


@admin_routes.put("/api/bluetooth/prefs")
async def bluetooth_prefs(request: Request, _: str = Depends(require_admin)):
    body = await _body(request)
    try:
        store.update_globals(body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _view(await service.refresh())


@public_routes.get("/api/bluetooth/gamepads")
async def bluetooth_gamepads(request: Request):
    require_display(request)
    return JSONResponse({"rev": service.input_rev, "gamepads": gamepads(service.state["devices"])}, headers=NO_CACHE)
