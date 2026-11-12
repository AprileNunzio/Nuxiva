import logging
import re
import time

import httpx

log = logging.getLogger("nuxiva.rpa")
REPOSITORY = "AprileNunzio/NUXIVA"
API = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=20"
INSTALLER = "NUXIVA_Assistente_Setup.exe"
CACHE_SECONDS = 3600
TAG_RE = re.compile(r"assistant-v(\d+(?:\.\d+){1,3})")
_cache: dict[bool, tuple[float, str]] = {}


def pick(releases: list, enrolled: bool = False) -> str:
    best: tuple = ()
    for release in releases:
        match = TAG_RE.fullmatch(str(release.get("tag_name", "")))
        if not match or release.get("draft") or release.get("prerelease"):
            continue
        assets = {asset.get("name"): asset.get("browser_download_url") for asset in release.get("assets") or []}
        url = assets.get(INSTALLER)
        key = tuple(int(n) for n in match.group(1).split("."))
        if enrolled:
            expected = f"https://github.com/{REPOSITORY}/releases/download/{match[0]}/{INSTALLER}"
            if (key <= (5, 3, 0) or not assets.get("manifest.json") or not assets.get("manifest.sig")
                    or not isinstance(url, str) or url.casefold() != expected.casefold()):
                continue
        if url and (not best or key > best[0]):
            best = (key, url)
    return best[1] if best else ""


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
