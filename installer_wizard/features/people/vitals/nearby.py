import hashlib
import re
import threading
import time

SEARCH_SECONDS = 90.0
FRESH_SECONDS = 30.0
MAX_FOUND = 30
MAX_NAME = 40
HEALTH_SERVICES = {"180d", "1809", "1822"}
VENDORS = re.compile(r"fitbit|polar|garmin|suunto|coros|whoop|oura|amazfit|zepp|mi (smart )?band|xiaomi|huawei|honor|galaxy (watch|fit|ring)|pixel watch|apple watch|withings|wahoo|scosche|magene|wear os|tickr|h10|h9|verity|forerunner|fenix|ionic|versa", re.I)
MAC = re.compile(r"^[0-9A-F]{2}(:[0-9A-F]{2}){5}$")


def ref_of(address: str) -> str:
    return hashlib.sha256(address.encode()).hexdigest()[:10]


def level_of(rssi: float) -> int:
    return 4 if rssi >= -55 else 3 if rssi >= -67 else 2 if rssi >= -80 else 1


def relevant(row: dict) -> bool:
    services = {str(s).lower()[4:8] if len(str(s)) > 8 else str(s).lower().removeprefix("0x") for s in row.get("services") or []}
    return bool(services & HEALTH_SERVICES) or bool(VENDORS.search(row.get("name", "")))


class Nearby:
    def __init__(self) -> None:
        self._searches: dict[str, float] = {}
        self._found: dict[str, dict] = {}
        self._lock = threading.Lock()

    def start(self, slug: str, now: float | None = None) -> None:
        with self._lock:
            self._searches[slug] = (now or time.time()) + SEARCH_SECONDS

    def stop(self, slug: str) -> None:
        with self._lock:
            self._searches.pop(slug, None)

    def active(self, now: float | None = None) -> bool:
        now = now or time.time()
        with self._lock:
            self._searches = {s: t for s, t in self._searches.items() if t > now}
            return bool(self._searches)

    def searching(self, slug: str, now: float | None = None) -> bool:
        return self._searches.get(slug, 0.0) > (now or time.time())

    def report(self, node: str, rows, now: float | None = None) -> int:
        now = now or time.time()
        if not self.active(now):
            return 0
        added = 0
        for row in [r for r in (rows or [])[:60] if isinstance(r, dict)]:
            address = str(row.get("address", "")).upper()
            if not MAC.match(address):
                continue
            try:
                rssi = float(row.get("rssi"))
            except (TypeError, ValueError):
                continue
            clean = {"address": address, "name": " ".join(str(row.get("name") or "").split())[:MAX_NAME],
                     "services": [str(s)[:40] for s in (row.get("services") or [])[:8]]}
            if not relevant(clean):
                continue
            with self._lock:
                held = self._found.get(address)
                if held is None or held["node"] == node or rssi > held["rssi"] + 4 or now - held["at"] > FRESH_SECONDS:
                    self._found[address] = {**clean, "rssi": max(-127.0, min(0.0, rssi)), "node": node, "at": now}
                    added += 1
        return added

    def listing(self, taken: set, now: float | None = None) -> list[dict]:
        now = now or time.time()
        with self._lock:
            rows = [r for r in self._found.values() if now - r["at"] <= FRESH_SECONDS and r["address"] not in taken]
        rows.sort(key=lambda r: -r["rssi"])
        return [{"ref": ref_of(r["address"]), "name": r["name"] or "", "level": level_of(r["rssi"]), "node": r["node"],
                 "standard": bool({s.lower()[4:8] for s in r["services"] if len(s) > 8} & HEALTH_SERVICES)} for r in rows[:MAX_FOUND]]

    def resolve(self, ref: str, now: float | None = None) -> str:
        now = now or time.time()
        with self._lock:
            for row in self._found.values():
                if ref_of(row["address"]) == ref and now - row["at"] <= FRESH_SECONDS * 4:
                    return row["address"]
        return ""


nearby = Nearby()
