import json
import logging
import re
import time
import unicodedata
from datetime import datetime, timezone

import httpx

from config import STATE_DIR
from sealed import write_private

log = logging.getLogger("nuxiva.weather.alerts")
REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
METEOALARM_URL = "https://feeds.meteoalarm.org/api/v1/warnings/feeds-{}"
NWS_URL = "https://api.weather.gov/alerts/active"
AGENT = "Nuxiva-weather/1.0 (home assistant)"
AREA_FILE = STATE_DIR / "weather" / "areas.json"
REFRESH = 900
MAX_ALERTS = 8
TEXT_MAX = 600
SEVERITIES = ("minor", "moderate", "severe", "extreme")
COUNTRIES = {
    "it": "italy", "fr": "france", "es": "spain", "de": "germany", "at": "austria", "ch": "switzerland", "gb": "united-kingdom",
    "pt": "portugal", "nl": "netherlands", "be": "belgium", "gr": "greece", "hr": "croatia", "si": "slovenia", "ie": "ireland",
    "pl": "poland", "cz": "czechia", "sk": "slovakia", "hu": "hungary", "ro": "romania", "bg": "bulgaria", "dk": "denmark",
    "se": "sweden", "no": "norway", "fi": "finland", "ee": "estonia", "lv": "latvia", "lt": "lithuania", "lu": "luxembourg",
    "mt": "malta", "cy": "cyprus", "rs": "serbia", "me": "montenegro", "is": "iceland", "md": "moldova",
}
LEVEL_RE = re.compile(r"\b(yellow|orange|red|green)\b", re.I)
cache: dict[str, tuple[float, list]] = {}


class AlertsUnavailable(RuntimeError):
    pass


def clean(value, limit: int = TEXT_MAX) -> str:
    text = "".join(ch for ch in str(value or "") if unicodedata.category(ch)[0] != "C" or ch in "\n")
    return re.sub(r"\s+", " ", text).strip()[:limit]


def fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", "".join(ch for ch in text if not unicodedata.combining(ch))).strip()


def _key(place: dict) -> str:
    return f"{float(place['lat']):.2f},{float(place['lon']):.2f}"


def _areas() -> dict:
    try:
        data = json.loads(AREA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


async def area(client: httpx.AsyncClient, place: dict) -> dict:
    known = _areas()
    hit = known.get(_key(place))
    if isinstance(hit, dict) and hit.get("country"):
        return hit
    response = await client.get(REVERSE_URL, params={"lat": place["lat"], "lon": place["lon"], "format": "jsonv2", "zoom": 10,
                                                     "accept-language": "en"})
    response.raise_for_status()
    address = (response.json() or {}).get("address") or {}
    found = {"country": clean(address.get("country_code"), 2).lower(),
             "names": [clean(address.get(k), 80) for k in ("city", "town", "village", "county", "province", "state_district", "state", "region")
                       if address.get(k)]}
    if len(known) < 256:
        known[_key(place)] = found
        AREA_FILE.parent.mkdir(parents=True, exist_ok=True)
        write_private(AREA_FILE, json.dumps(known, ensure_ascii=False).encode())
    return found


def _severity(value) -> str:
    text = str(value or "").lower()
    return text if text in SEVERITIES else "moderate"


def _stamp(value) -> str:
    text = clean(value, 40)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except ValueError:
        return ""


def _live(expires: str, now: datetime) -> bool:
    return not expires or datetime.fromisoformat(expires) > now


def meteoalarm(raw: dict, names: list[str], language: str, now: datetime) -> list[dict]:
    wanted = [fold(n) for n in names if fold(n)]
    out = []
    for warning in (raw or {}).get("warnings") or []:
        infos = ((warning or {}).get("alert") or {}).get("info") or []
        if not infos:
            continue
        info = next((i for i in infos if str(i.get("language", "")).lower().startswith(language)), infos[0])
        regions = [clean(a.get("areaDesc"), 120) for a in info.get("area") or [] if isinstance(a, dict)]
        matched = next((r for r in regions if any(w and (w in fold(r) or fold(r) in w) for w in wanted)), None)
        if not matched:
            continue
        params = {str(p.get("valueName")): str(p.get("value")) for p in info.get("parameter") or [] if isinstance(p, dict)}
        level = LEVEL_RE.search(params.get("awareness_level", ""))
        expires = _stamp(info.get("expires"))
        if level and level.group(1).lower() == "green" or not _live(expires, now):
            continue
        out.append({"source": "MeteoAlarm", "event": clean(info.get("event"), 120), "severity": _severity(info.get("severity")),
                    "level": level.group(1).lower() if level else "", "headline": clean(info.get("headline"), 200),
                    "description": clean(info.get("description")), "onset": _stamp(info.get("onset")), "expires": expires, "area": matched})
    return out


def nws(raw: dict, now: datetime) -> list[dict]:
    out = []
    for feature in (raw or {}).get("features") or []:
        p = (feature or {}).get("properties") or {}
        expires = _stamp(p.get("ends") or p.get("expires"))
        if not _live(expires, now):
            continue
        out.append({"source": "NWS", "event": clean(p.get("event"), 120), "severity": _severity(p.get("severity")), "level": "",
                    "headline": clean(p.get("headline"), 200), "description": clean(p.get("description")),
                    "onset": _stamp(p.get("onset") or p.get("effective")), "expires": expires, "area": clean(p.get("areaDesc"), 120)})
    return out


def ranked(items: list[dict]) -> list[dict]:
    unique = {(a["source"], a["event"], a["onset"], a["area"]): a for a in items}
    return sorted(unique.values(), key=lambda a: (-SEVERITIES.index(a["severity"]), a["onset"]))[:MAX_ALERTS]


async def official(place: dict, language: str = "it") -> list[dict]:
    key = _key(place)
    hit = cache.get(key)
    if hit and time.time() - hit[0] < REFRESH:
        return hit[1]
    now = datetime.now(timezone.utc)
    try:
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": AGENT}) as client:
            where = await area(client, place)
            country = where.get("country", "")
            if country == "us":
                response = await client.get(NWS_URL, params={"point": f"{float(place['lat']):.4f},{float(place['lon']):.4f}"},
                                            headers={"Accept": "application/geo+json"})
                response.raise_for_status()
                found = nws(response.json(), now)
            elif country in COUNTRIES:
                response = await client.get(METEOALARM_URL.format(COUNTRIES[country]))
                response.raise_for_status()
                found = meteoalarm(response.json(), [*where.get("names", []), place.get("name", "")], language, now)
            else:
                found = []
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        if hit:
            return hit[1]
        raise AlertsUnavailable(type(exc).__name__) from exc
    result = ranked(found)
    cache[key] = (time.time(), result)
    return result
