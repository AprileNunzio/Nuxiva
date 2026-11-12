import asyncio
import importlib.util
import logging
import time

from config import env_get
from agenti.bluetooth import adapter
from agenti.medico.vitals.ble_codec import HR_CHAR, METRICS_OF, PARSERS, RrWindow, nearby_rows, rr_intervals
from agenti.medico.vitals.book import book
from agenti.medico.vitals.nearby import nearby

log = logging.getLogger("nuxiva.vitals")
NODE_ID = "server"
NODE_NAME = "Server"
SCAN_SECONDS = 6.0
PAUSE_SECONDS = 2.0
IDLE_SECONDS = 20.0
CONNECT_TIMEOUT = 10.0
MAX_SAMPLES = 200
MAX_BUFFER = 2000


class LocalBle:
    def __init__(self) -> None:
        self.ready = False
        self.watch: list[str] = []
        self.clients: dict = {}
        self.samples: list[dict] = []
        self.errors: list[dict] = []
        self.profiles: dict[str, list[str]] = {}
        self.rr: dict[str, RrWindow] = {}
        self.dropped: set[str] = set()
        self.discover = False
        self.last_error = ""

    @staticmethod
    def enabled() -> bool:
        return env_get("NUXIVA_VITALS_LOCAL_BLE", "1") != "0" and importlib.util.find_spec("bleak") is not None

    def available(self) -> bool:
        return self.ready

    @staticmethod
    def blockers() -> list[str]:
        found = []
        if env_get("NUXIVA_VITALS_LOCAL_BLE", "1") == "0":
            found.append("local_disabled")
        elif importlib.util.find_spec("bleak") is None:
            found.append("bleak_missing")
        elif not adapter.has_adapter():
            found.append("no_adapter")
        return found

    def wanted(self, now: float) -> bool:
        return bool(book.addresses()) or nearby.active(now)

    async def _scan(self) -> dict:
        from bleak import BleakScanner
        try:
            return await BleakScanner.discover(timeout=SCAN_SECONDS, return_adv=True)
        except Exception as exc:
            self.errors.append({"address": "", "code": "scan_failed"})
            log.info("Scansione BLE del server non riuscita: %s", exc)
            return {}

    def _notifier(self, address: str, char: str, parser):
        def notify(_, data) -> None:
            now, raw = time.time(), bytes(data)
            rows = parser(raw)
            if char == HR_CHAR:
                rmssd = self.rr.setdefault(address, RrWindow()).add(rr_intervals(raw))
                if rmssd:
                    rows.append(("hrv", rmssd))
            self.samples.extend({"address": address, "metric": m, "value": v, "ts": now} for m, v in rows)
            if len(self.samples) > MAX_BUFFER:
                del self.samples[:len(self.samples) - MAX_BUFFER]
        return notify

    async def _drop(self, address: str) -> None:
        self.rr.pop(address, None)
        client = self.clients.pop(address, None)
        if client:
            try:
                await client.disconnect()
            except Exception as exc:
                log.info("Disconnessione BLE %s: %s", address, exc)

    async def _connect(self, address: str) -> None:
        from bleak import BleakClient
        client = BleakClient(address)
        usable: list[str] = []
        linked = False
        try:
            await client.connect(timeout=CONNECT_TIMEOUT)
            linked = True
            for char, parser in PARSERS.items():
                if not client.services.get_characteristic(char):
                    continue
                try:
                    await client.start_notify(char, self._notifier(address, char, parser))
                    usable += METRICS_OF[char]
                except Exception as exc:
                    log.info("Profilo %s di %s non attivato: %s", char[4:8], address, exc)
        except Exception as exc:
            self.errors.append({"address": address, "code": "connect_failed"})
            log.info("Connessione BLE a %s non riuscita: %s", address, exc)
        if linked:
            self.profiles[address] = sorted(set(usable))
        if usable and client.is_connected:
            self.clients[address] = client
            return
        try:
            if client.is_connected:
                await client.disconnect()
        except Exception as exc:
            log.info("Chiusura BLE %s: %s", address, exc)

    async def cycle(self) -> None:
        found = await self._scan()
        watch = set(self.watch)
        seen = [{"address": a.upper(), "rssi": adv.rssi} for a, (_, adv) in found.items() if a.upper() in watch][:40]
        report = {"seen": seen, "samples": self.samples[:MAX_SAMPLES], "errors": self.errors[:20], "profiles": dict(self.profiles),
                  "nearby": nearby_rows(found) if self.discover else []}
        self.samples, self.errors, self.profiles = self.samples[MAX_SAMPLES:], self.errors[20:], {}
        from agenti.medico.vitals import service
        res = service.node_report(NODE_ID, report)
        self.discover = bool(res.get("discover"))
        self.watch = [str(a).upper() for a in res.get("watch") or []]
        wanted = {str(a).upper() for a in res.get("connect") or []}
        for row in res.get("drop") or []:
            address, nonce = str(row.get("address", "")).upper(), str(row.get("nonce", ""))
            if nonce and nonce not in self.dropped:
                self.dropped.add(nonce)
                wanted.discard(address)
                await self._drop(address)
        for address in list(self.clients):
            if address not in wanted or not self.clients[address].is_connected:
                await self._drop(address)
        for address in wanted - set(self.clients):
            await self._connect(address)

    async def run(self) -> None:
        if not self.enabled():
            return
        while True:
            try:
                self.ready = adapter.has_adapter()
                if self.ready and self.wanted(time.time()):
                    await self.cycle()
                    await asyncio.sleep(PAUSE_SECONDS)
                else:
                    for address in list(self.clients):
                        await self._drop(address)
                    await asyncio.sleep(IDLE_SECONDS if self.ready else 60.0)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"[:160]
                log.warning("Ciclo Bluetooth dei parametri vitali: %s", exc)
                await asyncio.sleep(IDLE_SECONDS)


local_ble = LocalBle()
