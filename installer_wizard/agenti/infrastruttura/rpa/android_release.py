import logging
import re
import time

import httpx

from agenti.rpa import releases

log = logging.getLogger("nuxiva.rpa")
APK = "Nuxiva.apk"
LEGACY_APK = "Nuxiva_Node.apk"
TAG_RE = re.compile(r"android-v(\d+(?:\.\d+){1,3})")
CACHE_SECONDS = 3600
_cache: tuple[float, dict] = (0.0, {})


def newest(items: list) -> dict:
    best: dict = {}
    for release in items:
        tag = str(release.get("tag_name", ""))
        match = TAG_RE.fullmatch(tag)
        if not match or release.get("draft") or release.get("prerelease"):
            continue
        assets = {a.get("name"): a for a in release.get("assets") or [] if isinstance(a, dict)}
        name = APK if APK in assets else LEGACY_APK
        asset = assets.get(name)
        url = asset.get("browser_download_url") if asset else None
        if not isinstance(url, str) or url.casefold() != releases._official(tag, name).casefold():
            continue
        digest = releases._digest(asset.get("digest"))
        if not digest:
            continue
        key = tuple(int(n) for n in match.group(1).split("."))
        if not best or key > best["key"]:
            best = {"key": key, "version": match.group(1), "name": name, "url": url, "sha256": digest}
    return {k: v for k, v in best.items() if k != "key"}


async def info() -> dict:
    global _cache
    cached_at, cached = _cache
    if cached and time.monotonic() - cached_at < CACHE_SECONDS:
        return cached
    try:
        async with httpx.AsyncClient(timeout=10, headers={"Accept": "application/vnd.github+json"}) as client:
            response = await client.get(releases.API)
        response.raise_for_status()
        found = newest(response.json())
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("Release dell'app Android non leggibili da GitHub: %s", exc)
        return cached
    _cache = (time.monotonic(), found)
    return found
