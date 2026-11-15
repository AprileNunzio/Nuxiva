from __future__ import annotations

import logging
import time

log = logging.getLogger("nuxiva-node")

HR_CHAR = "00002a37-0000-1000-8000-00805f9b34fb"
TEMP_CHAR = "00002a1c-0000-1000-8000-00805f9b34fb"
PLX_CHARS = ("00002a5e-0000-1000-8000-00805f9b34fb", "00002a5f-0000-1000-8000-00805f9b34fb")
VITALS_SCAN = 5.0
VITALS_PAUSE = 3.0


def sfloat(raw: int) -> float | None:
    if raw in (0x07FF, 0x0800, 0x0801, 0x07FE, 0x0802):
        return None
    mantissa, exponent = raw & 0x0FFF, raw >> 12
    mantissa -= 0x1000 if mantissa >= 0x800 else 0
    exponent -= 0x10 if exponent >= 0x8 else 0
    return mantissa * 10 ** exponent


def ieee_float(raw: int) -> float | None:
    if raw in (0x007FFFFF, 0x00800000, 0x00800001, 0x007FFFFE, 0x00800002):
        return None
    mantissa, exponent = raw & 0xFFFFFF, raw >> 24
    mantissa -= 0x1000000 if mantissa >= 0x800000 else 0
    exponent -= 0x100 if exponent >= 0x80 else 0
    return mantissa * 10 ** exponent


def parse_heart_rate(data: bytes) -> list[tuple[str, float]]:
    if len(data) < (3 if data and data[0] & 1 else 2):
        return []
    return [("heart_rate", int.from_bytes(data[1:3], "little") if data[0] & 1 else data[1])]


def parse_temperature(data: bytes) -> list[tuple[str, float]]:
    if len(data) < 5:
        return []
    value = ieee_float(int.from_bytes(data[1:5], "little"))
    if value is None:
        return []
    return [("body_temp", round((value - 32) * 5 / 9 if data[0] & 1 else value, 1))]


def parse_oximeter(data: bytes) -> list[tuple[str, float]]:
    if len(data) < 5:
        return []
    spo2, pulse = sfloat(int.from_bytes(data[1:3], "little")), sfloat(int.from_bytes(data[3:5], "little"))
    rows = [("spo2", round(spo2))] if spo2 is not None else []
    return rows + ([("heart_rate", round(pulse))] if pulse is not None else [])


PARSERS = {HR_CHAR: parse_heart_rate, TEMP_CHAR: parse_temperature, PLX_CHARS[0]: parse_oximeter, PLX_CHARS[1]: parse_oximeter}


async def vitals_cycle(cfg: dict, headers: dict, state: dict, post) -> None:
    import asyncio
    from bleak import BleakClient, BleakScanner
    try:
        found = await BleakScanner.discover(timeout=VITALS_SCAN, return_adv=True)
    except Exception as exc:
        state["errors"].append({"address": "", "code": "scan_failed"})
        log.info("Scansione BLE non riuscita: %s", exc)
        found = {}
    watch = set(state["watch"])
    seen = [{"address": a.upper(), "rssi": adv.rssi} for a, (_, adv) in found.items() if a.upper() in watch][:40]
    nearby = nearby_devices(found) if state["discover"] else []
    samples, state["samples"] = state["samples"][:200], state["samples"][200:]
    errors, state["errors"] = state["errors"][:20], state["errors"][20:]
    profiles, state["profiles"] = dict(state["profiles"]), {}
    res = await asyncio.to_thread(post, cfg["server"], "/api/vitals/node",
                                  {"seen": seen, "samples": samples, "nearby": nearby, "errors": errors, "profiles": profiles}, headers)
    state["discover"] = bool(res.get("discover"))
    state["watch"] = [str(a).upper() for a in res.get("watch") or []]
    wanted = {str(a).upper() for a in res.get("connect") or []}
    for row in res.get("drop") or []:
        address, nonce = str(row.get("address", "")).upper(), str(row.get("nonce", ""))
        if nonce and nonce not in state["dropped"]:
            state["dropped"].add(nonce)
            wanted.discard(address)
            client = state["clients"].pop(address, None)
            if client:
                try:
                    await client.disconnect()
                except Exception as exc:
                    log.info("Disconnessione BLE %s: %s", address, exc)
    for address in list(state["clients"]):
        if address not in wanted or not state["clients"][address].is_connected:
            client = state["clients"].pop(address)
            try:
                await client.disconnect()
            except Exception as exc:
                log.info("Disconnessione BLE %s: %s", address, exc)
    for address in wanted - set(state["clients"]):
        client = BleakClient(address)
        try:
            await client.connect(timeout=10.0)
            usable = []
            for char, parser in PARSERS.items():
                if client.services.get_characteristic(char):
                    usable += METRICS_OF[char]
                    def notify(_, data, address=address, parser=parser):
                        now = time.time()
                        state["samples"].extend({"address": address, "metric": m, "value": v, "ts": now} for m, v in parser(bytes(data)))
                    await client.start_notify(char, notify)
            state["profiles"][address] = sorted(set(usable))
            if usable:
                state["clients"][address] = client
            else:
                await client.disconnect()
        except Exception as exc:
            state["errors"].append({"address": address, "code": "connect_failed"})
            log.info("Connessione BLE a %s non riuscita: %s", address, exc)


METRICS_OF = {HR_CHAR: ["heart_rate"], TEMP_CHAR: ["body_temp"], PLX_CHARS[0]: ["spo2", "heart_rate"], PLX_CHARS[1]: ["spo2", "heart_rate"]}
HEALTH_SERVICES = ("180d", "1809", "1822")


def nearby_devices(found: dict) -> list[dict]:
    rows = []
    for address, (device, adv) in found.items():
        name = (adv.local_name or getattr(device, "name", "") or "")[:40]
        services = [u for u in adv.service_uuids or [] if str(u).lower()[4:8] in HEALTH_SERVICES]
        if name or services:
            rows.append({"address": address.upper(), "name": name, "rssi": adv.rssi, "services": services[:8]})
    return sorted(rows, key=lambda r: -(r["rssi"] or -127))[:40]


def vitals_loop(cfg: dict, post) -> None:
    import asyncio
    headers = {"Authorization": f"Bearer {cfg['token']}", "X-Nuxiva-Node": cfg["id"]}
    state = {"watch": [], "clients": {}, "samples": [], "discover": False, "errors": [], "profiles": {}, "dropped": set()}

    async def run() -> None:
        while True:
            try:
                await vitals_cycle(cfg, headers, state, post)
            except Exception as exc:
                log.info("Ciclo parametri vitali: %s", exc)
            await asyncio.sleep(VITALS_PAUSE)
    asyncio.run(run())


def start(cfg: dict, post) -> None:
    import threading
    threading.Thread(target=vitals_loop, args=(cfg, post), daemon=True, name="vitals").start()
    log.info("Lettura dei parametri vitali via Bluetooth attiva")
