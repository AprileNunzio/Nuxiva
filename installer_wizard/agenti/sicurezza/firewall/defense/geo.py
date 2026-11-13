import bisect
import gzip
import hashlib
import io
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone

from config import STATE_DIR

from agenti.firewall.defense import netaddr

GEO_DIR = STATE_DIR / "firewall" / "geo"
TABLE_FILE = GEO_DIR / "country.csv"
META_FILE = GEO_DIR / "meta.json"
SOURCE = "https://download.db-ip.com/free/dbip-country-lite-{month}.csv.gz"
ATTRIBUTION = "IP Geolocation by DB-IP (https://db-ip.com), CC BY 4.0"
MAX_DOWNLOAD = 64 * 1024 * 1024
MAX_TABLE = 256 * 1024 * 1024
MAX_ROWS = 4_000_000
REFRESH_DAYS = 30
log = logging.getLogger("nuxiva.firewall")


class GeoError(ValueError):
    pass


def _country(raw: str) -> str | None:
    text = raw.strip().strip('"')
    return text if len(text) == 2 and "A" <= text[0] <= "Z" and "A" <= text[1] <= "Z" and text != "ZZ" else None


class PyTable:

    def __init__(self) -> None:
        self.starts = {4: [], 6: []}
        self.rows = {4: [], 6: []}

    def parse(self, text: str) -> int:
        rows, bad, count = {4: [], 6: []}, 0, 0
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            count += 1
            if count > MAX_ROWS:
                raise GeoError("geo.too_large")
            parts = line.split(",")
            if len(parts) < 3:
                bad += 1
                continue
            first, last = netaddr.ip(parts[0].strip('"')), netaddr.ip(parts[1].strip('"'))
            code = _country(parts[2])
            if first is not None and last is not None and code and first.version == last.version and first <= last:
                rows[first.version].append((int(first), int(last), code))
            elif code is None and parts[2].strip().strip('"') in ("ZZ", ""):
                continue
            else:
                bad += 1
        size = len(rows[4]) + len(rows[6])
        if size == 0:
            raise GeoError("geo.empty")
        if bad * 100 > size:
            raise GeoError("geo.corrupt")
        for version in (4, 6):
            rows[version].sort(key=lambda r: r[0])
            if any(a[1] >= b[0] for a, b in zip(rows[version], rows[version][1:])):
                raise GeoError("geo.corrupt")
        self.rows = rows
        self.starts = {v: [r[0] for r in rows[v]] for v in (4, 6)}
        return size

    def lookup(self, raw: str) -> str | None:
        value = netaddr.ip(raw)
        if value is None:
            return None
        key = int(value)
        index = bisect.bisect_right(self.starts[value.version], key) - 1
        if index < 0:
            return None
        start, end, code = self.rows[value.version][index]
        return code if key <= end else None

    def size(self) -> int:
        return len(self.rows[4]) + len(self.rows[6])


def _native_table():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    factory = getattr(nuxiva_native, "RustGeo", None)
    return factory() if factory else None


class Geo:

    def __init__(self, native: bool = True) -> None:
        self.lock = threading.RLock()
        self.table = (_native_table() if native else None) or PyTable()
        self.loaded = False
        self.cache: dict[str, str | None] = {}

    @property
    def engine(self) -> str:
        return "python" if isinstance(self.table, PyTable) else "rust"

    def parse(self, text: str) -> int:
        with self.lock:
            try:
                size = self.table.parse(text)
            except ValueError as exc:
                raise GeoError(str(exc).split(":")[0]) from None
            self.cache.clear()
            self.loaded = True
            return size

    def load(self) -> int:
        try:
            if TABLE_FILE.stat().st_size > MAX_TABLE:
                raise GeoError("geo.too_large")
            text = TABLE_FILE.read_text(encoding="utf-8")
        except FileNotFoundError:
            return 0
        return self.parse(text)

    def lookup(self, raw: str) -> str:
        if not self.loaded:
            return ""
        key = netaddr.canonical(raw)
        address = netaddr.address(key)
        if address is None or netaddr.is_lan(address):
            return ""
        with self.lock:
            if key not in self.cache:
                if len(self.cache) > 20_000:
                    self.cache.clear()
                self.cache[key] = self.table.lookup(key)
            return self.cache[key] or ""

    def countries(self, addresses) -> dict[str, str]:
        found = {}
        for raw in addresses:
            code = self.lookup(raw)
            if code:
                found[netaddr.canonical(raw)] = code
        return found

    def status(self) -> dict:
        try:
            meta = json.loads(META_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
        return {"loaded": self.loaded, "rows": self.table.size() if self.loaded else 0, "engine": self.engine,
                "updated": meta.get("at", 0), "month": meta.get("month", ""), "sha256": meta.get("sha256", ""),
                "attribution": ATTRIBUTION}

    def stale(self) -> bool:
        return time.time() - float(self.status()["updated"] or 0) > REFRESH_DAYS * 86_400


def months(now: datetime | None = None) -> list[str]:
    current = now or datetime.now(timezone.utc)
    previous = current.replace(day=1) - timedelta(days=1)
    return [current.strftime("%Y-%m"), previous.strftime("%Y-%m")]


def unpack(blob: bytes) -> str:
    if len(blob) > MAX_DOWNLOAD:
        raise GeoError("geo.too_large")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(blob)) as stream:
            data = stream.read(MAX_TABLE + 1)
    except (OSError, EOFError):
        raise GeoError("geo.corrupt") from None
    if len(data) > MAX_TABLE:
        raise GeoError("geo.too_large")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise GeoError("geo.corrupt") from None


def install(text: str, month: str) -> int:
    probe = Geo()
    size = probe.parse(text)
    GEO_DIR.mkdir(parents=True, exist_ok=True)
    tmp = TABLE_FILE.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(TABLE_FILE)
    meta = {"at": time.time(), "month": month, "rows": size, "sha256": hashlib.sha256(text.encode()).hexdigest()}
    META_FILE.write_text(json.dumps(meta), encoding="utf-8")
    return size


async def refresh() -> dict:
    import httpx
    errors = []
    for month in months():
        url = SOURCE.format(month=month)
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
                async with client.stream("GET", url) as response:
                    if response.status_code != 200:
                        errors.append(f"{month}: HTTP {response.status_code}")
                        continue
                    chunks, total = [], 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > MAX_DOWNLOAD:
                            raise GeoError("geo.too_large")
                        chunks.append(chunk)
        except httpx.HTTPError as exc:
            errors.append(f"{month}: {type(exc).__name__}")
            continue
        size = install(unpack(b"".join(chunks)), month)
        geo.load()
        log.info("Database dei paesi aggiornato (%s, %d intervalli)", month, size)
        return {"ok": True, "month": month, "rows": size}
    return {"ok": False, "errors": errors}


geo = Geo()
