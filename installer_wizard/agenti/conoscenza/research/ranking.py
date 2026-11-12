import time
from urllib.parse import urlsplit

TRUSTED = {
    "ansa.it", "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "repubblica.it", "corriere.it", "ilsole24ore.com", "lastampa.it",
    "wikipedia.org", "who.int", "nasa.gov", "europa.eu", "agi.it", "rainews.it", "skytg24.it", "ilpost.it", "gazzetta.it",
    "legaseriea.it", "uefa.com", "fifa.com", "formula1.com", "espn.com", "theguardian.com", "nytimes.com", "lemonde.fr", "elpais.com",
    "nature.com", "science.org", "istat.it", "ec.europa.eu", "meteo.it", "ilmeteo.it", "protezionecivile.gov.it",
}
OFFICIAL_SUFFIXES = (".gov", ".gov.it", ".edu", ".ac.uk", ".europa.eu", ".int", ".mil")
BLOCKED = {
    "pinterest.com", "quora.com", "facebook.com", "instagram.com", "tiktok.com", "x.com", "twitter.com", "reddit.com", "youtube.com",
    "medium.com", "blogspot.com", "wordpress.com", "tumblr.com", "scribd.com", "yahoo.com",
}
LEVELS = (("alta", 0.85), ("media", 0.5), ("bassa", 0.0))


def domain_of(url_or_host: str) -> str:
    host = urlsplit(url_or_host if "//" in url_or_host else f"//{url_or_host}").hostname or ""
    return host.lower().removeprefix("www.")


def _matches(host: str, names: set[str]) -> bool:
    return any(host == name or host.endswith("." + name) for name in names)


def blocked(host: str) -> bool:
    return _matches(host, BLOCKED)


def reliability(host: str) -> float:
    if _matches(host, TRUSTED) or host.endswith(OFFICIAL_SUFFIXES):
        return 0.9
    if host.endswith((".it", ".com", ".org", ".net", ".eu")):
        return 0.5
    return 0.35


def label(score: float) -> str:
    return next(name for name, floor in LEVELS if score >= floor)


def freshness(published: float | None, now: float | None = None) -> float:
    if published is None:
        return 0.3
    age_days = max(0.0, ((now or time.time()) - published) / 86400)
    return 1.0 if age_days <= 1 else 0.8 if age_days <= 7 else 0.55 if age_days <= 31 else 0.3 if age_days <= 366 else 0.1


def score(host: str, published: float | None, now: float | None = None) -> float:
    return round(0.6 * reliability(host) + 0.4 * freshness(published, now), 4)
