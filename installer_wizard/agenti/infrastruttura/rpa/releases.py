import logging
import re
import time

import httpx

log = logging.getLogger("nuxiva.rpa")
REPOSITORY = "AprileNunzio/Nuxiva"
API = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=20"
INSTALLER = "Nuxiva_Setup.exe"
LEGACY_INSTALLER = "NUXIVA_Assistente_Setup.exe"
CACHE_SECONDS = 3600
TAG_RE = re.compile(r"assistant-v(\d+(?:\.\d+){1,3})")
_cache: dict[bool, tuple[float, str]] = {}
_info: dict[str, tuple[float, dict]] = {}


def _official(tag: str, name: str) -> str:
    return f"https://github.com/{REPOSITORY}/releases/download/{tag}/{name}"


def newest(releases: list) -> dict:
    best: dict = {}
    for release in releases:
        tag = str(release.get("tag_name", ""))
        match = TAG_RE.fullmatch(tag)
        if not match or release.get("draft") or release.get("prerelease"):
            continue
        assets = {asset.get("name"): asset.get("browser_download_url") for asset in release.get("assets") or []}
        for name in (INSTALLER, LEGACY_INSTALLER):
            url = assets.get(name)
            if isinstance(url, str) and url.casefold() == _official(tag, name).casefold():
                key = tuple(int(n) for n in match.group(1).split("."))
                if not best or key > best["key"]:
                    best = {"key": key, "version": match.group(1), "name": name, "url": url,
                            "signed": bool(assets.get("manifest.json") and assets.get("manifest.sig"))}
                break
    return best


def pick(releases: list, enrolled: bool = False) -> str:
    best = newest(releases)
    if not best or (enrolled and (not best["signed"] or best["key"] <= (5, 3, 0))):
        return ""
    return best["url"]


async def installer_url(enrolled: bool = False) -> str:
    cached_at, cached_url = _cache.get(enrolled, (0.0, ""))
    if time.monotonic() - cached_at < CACHE_SECONDS and enrolled in _cache:
        return cached_url
    try:
        async with httpx.AsyncClient(timeout=10, headers={"Accept": "application/vnd.github+json"}) as client:
            response = await client.get(API)
        response.raise_for_status()
        url = pick(response.json(), enrolled)
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("Release dell'Assistente Windows non leggibili da GitHub: %s", exc)
        return cached_url
    _cache[enrolled] = (time.monotonic(), url)
    return url


async def installer_info() -> dict:
    cached_at, cached = _info.get("v", (0.0, {}))
    if time.monotonic() - cached_at < CACHE_SECONDS and "v" in _info:
        return cached
    try:
        async with httpx.AsyncClient(timeout=10, headers={"Accept": "application/vnd.github+json"}) as client:
            response = await client.get(API)
        response.raise_for_status()
        best = newest(response.json())
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("Release dell'Assistente Windows non leggibili da GitHub: %s", exc)
        return cached
    info = {"version": best["version"], "name": best["name"], "url": best["url"]} if best else {}
    _info["v"] = (time.monotonic(), info)
    return info
