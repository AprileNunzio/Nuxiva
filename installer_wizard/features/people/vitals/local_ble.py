import asyncio
import importlib.util
import logging
import time

from config import env_get
from features.bluetooth import adapter
from features.people.vitals.ble_codec import METRICS_OF, PARSERS, nearby_rows
from features.people.vitals.book import book
from features.people.vitals.nearby import nearby

log = logging.getLogger("nuxiva.vitals")
NODE_ID = "server"
NODE_NAME = "Server"
SCAN_SECONDS = 6.0
PAUSE_SECONDS = 2.0
IDLE_SECONDS = 20.0
CONNECT_TIMEOUT = 10.0
MAX_SAMPLES = 200


class LocalBle:
    def __init__(self) -> None:
        self.ready = False
        self.watch: list[str] = []
        self.clients: dict = {}
        self.samples: list[dict] = []
        self.errors: list[dict] = []
        self.profiles: dict[str, list[str]] = {}
        self.dropped: set[str] = set()
        self.discover = False

    @staticmethod
    def enabled() -> bool:
        return env_get("NUXIVA_VITALS_LOCAL_BLE", "1") != "0" and importlib.util.find_spec("bleak") is not None

    def available(self) -> bool:
        return self.ready

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

    def _notifier(self, address: str, parser):
        def notify(_, data) -> None:
            now = time.time()
            self.samples.extend({"address": address, "metric": m, "value": v, "ts": now} for m, v in parser(bytes(data)))
        return notify

    async def _drop(self, address: str) -> None:
        client = self.clients.pop(address, None)
        if client:
            try:
                await client.disconnect()
            except Exception as exc:
                log.info("Disconnessione BLE %s: %s", address, exc)

    async def _connect(self, address: str) -> None:
        from bleak import BleakClient
        client = BleakClient(address)
        try:
            await client.connect(timeout=CONNECT_TIMEOUT)
            usable: list[str] = []
            for char, parser in PARSERS.items():
                if client.services.get_characteristic(char):
                    usable += METRICS_OF[char]
                    await client.start_notify(char, self._notifier(address, parser))
            self.profiles[address] = sorted(set(usable))
            if usable:
                self.clients[address] = client
            else:
                await client.disconnect()
        except Exception as exc:
            self.errors.append({"address": address, "code": "connect_failed"})
            log.info("Connessione BLE a %s non riuscita: %s", address, exc)

    async def cycle(self) -> None:
        found = await self._scan()
        watch = set(self.watch)
        seen = [{"address": a.upper(), "rssi": adv.rssi} for a, (_, adv) in found.items() if a.upper() in watch][:40]
        report = {"seen": seen, "samples": self.samples[:MAX_SAMPLES], "errors": self.errors[:20], "profiles": dict(self.profiles),
                  "nearby": nearby_rows(found) if self.discover else []}
        self.samples, self.errors, self.profiles = self.samples[MAX_SAMPLES:], self.errors[20:], {}
        from features.people.vitals import service
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
                log.warning("Ciclo Bluetooth dei parametri vitali: %s", exc)
                await asyncio.sleep(IDLE_SECONDS)


local_ble = LocalBle()
