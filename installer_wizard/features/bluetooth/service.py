import asyncio
import hashlib
import json
import logging
import time

from config import env_get
from state import store as state_store

from features.bluetooth import adapter, store
from features.bluetooth.classes import describe
from features.bluetooth.hid import hid
from features.bluetooth.router import router
from features.bluetooth.text import translate

log = logging.getLogger("nuxiva.bluetooth")
TICK = 4
RECONNECT_EVERY = 30
SCAN_SECONDS = 20
FRESH_SECONDS = 3.0


def gamepads(devs: list[dict]) -> list[dict]:
    data = store.load()
    pads = []
    for d in devs:
        if not d["connected"] or "gamepad" not in d["capabilities"]:
            continue
        s = store.settings(data, d["mac"])
        if s["games_enabled"]:
            pads.append({"name": d["name"], "label": s["alias"] or d["name"], "kind": d["kind"],
                         "slot": s["player_slot"], "deadzone": s["deadzone"], "sensitivity": s["sensitivity"],
                         "invert_y": s["invert_y"], "vibration": s["vibration"]})
    return sorted(pads, key=lambda p: (p["slot"], p["name"]))


class BluetoothService:
    def __init__(self) -> None:
        self.state: dict = {"controller": {"present": False}, "devices": [], "routing": {}, "scanning": False}
        self.connected: set[str] = set()
        self.last_reconnect = 0.0
        self.prepared = False
        self.scanning_until = 0.0
        self.scan_task: asyncio.Task | None = None
        self.input_rev = ""
        self.updated_at = 0.0
        self.lock = asyncio.Lock()

    @staticmethod
    def enabled() -> bool:
        return env_get("NUXIVA_BLUETOOTH", "1") != "0"

    async def _prepare(self) -> None:
        from orchestrator import converge_steps
        self.prepared = True
        state_store.event("INFO", translate("event_preparing"), "bluetooth")
        await converge_steps(["bluetooth"], translate("event_new_adapter"))

    def _announce(self, devs: list[dict]) -> None:
        from features.desktop.desk import desk
        now = {d["mac"] for d in devs if d["connected"]}
        names = {d["mac"]: d["name"] for d in devs}
        data = store.load()
        for mac in now - self.connected:
            label = store.settings(data, mac)["alias"] or names.get(mac, mac)
            state_store.event("INFO", translate("event_connected", name=label), "bluetooth")
            if data["announce"]:
                desk.show("notice", {"icon": "🎧", "title": translate("notice_connected"), "text": label},
                          key=f"bt:{mac}")
        for mac in self.connected - now:
            state_store.event("INFO", translate("event_disconnected", name=names.get(mac, mac)), "bluetooth")
        self.connected = now

    async def _reconnect(self, devs: list[dict]) -> None:
        data = store.load()
        if not data["auto_connect"] or time.time() - self.last_reconnect < RECONNECT_EVERY:
            return
        self.last_reconnect = time.time()
        for d in devs:
            if d["paired"] and not d["connected"] and not d["blocked"] and store.settings(data, d["mac"])["autoconnect"]:
                try:
                    await adapter.connect(d["mac"])
                except adapter.BluetoothError as exc:
                    log.info("%s non raggiungibile: %s", d["name"], exc)

    def _publish(self, devs: list[dict], routing: dict) -> None:
        pads = gamepads(devs)
        rev = hashlib.sha256(json.dumps(pads, sort_keys=True).encode()).hexdigest()[:16] if pads else ""
        touched = False
        if rev != self.input_rev:
            self.input_rev = rev
            state_store.bt_input_rev = rev
            touched = True
        if routing.get("changed"):
            state_store.audio_rev = f"bt-{time.time():.0f}"
            touched = True
        if touched:
            state_store.touch()

    async def refresh(self) -> dict:
        async with self.lock:
            ctrl = await adapter.controller()
            ready = ctrl["present"] and ctrl["installed"]
            devs = [describe(d) for d in await adapter.devices()] if ready else []
            routing = await router.apply(devs) if devs else {}
            await hid.apply(devs)
            self._publish(devs, routing)
            self._announce(devs)
            self.state = {"controller": ctrl, "devices": devs, "routing": routing, "scanning": self.scanning()}
            self.updated_at = time.monotonic()
            return self.state

    async def current(self, max_age: float = FRESH_SECONDS) -> dict:
        if time.monotonic() - self.updated_at <= max_age:
            return self.state
        return await self.refresh()

    def scanning(self) -> bool:
        return time.time() < self.scanning_until

    def start_scan(self) -> int:
        if self.scan_task and not self.scan_task.done():
            return max(1, int(self.scanning_until - time.time()))
        self.scanning_until = time.time() + SCAN_SECONDS
        self.scan_task = asyncio.create_task(self._scan(SCAN_SECONDS))
        return SCAN_SECONDS

    async def _scan(self, seconds: int) -> None:
        try:
            await adapter.power(True)
            await adapter.scan(seconds)
        except (OSError, adapter.BluetoothError) as exc:
            log.warning("Ricerca Bluetooth non riuscita: %s", exc)
        finally:
            self.scanning_until = 0.0
        try:
            await self.refresh()
        except (OSError, ValueError, adapter.BluetoothError) as exc:
            log.warning("Aggiornamento Bluetooth dopo la ricerca non riuscito: %s", exc)

    async def run(self) -> None:
        while True:
            if self.enabled():
                try:
                    state = await self.refresh()
                    ctrl = state["controller"]
                    if ctrl["present"] and not ctrl["installed"] and not self.prepared:
                        await self._prepare()
                    elif ctrl["present"] and ctrl["installed"]:
                        await self._reconnect(state["devices"])
                except (OSError, ValueError, adapter.BluetoothError) as exc:
                    log.warning("Controllo Bluetooth non riuscito: %s", exc)
            await asyncio.sleep(TICK)


service = BluetoothService()
