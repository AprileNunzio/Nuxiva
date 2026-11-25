import httpx

from agenti.hands.holo.catalog import fetch

API = "https://api.polyhaven.com"
MAX_FILES = 64
NAME_MAX = 96


def _words(text: str) -> set[str]:
    from agenti.hands.holo.commands import norm
    return {w for w in norm(text).split() if len(w) > 2}


def _candidate(asset_id: str, item: dict, wanted: set[str]) -> dict | None:
    if not asset_id.replace("_", "").isalnum() or len(asset_id) > 64:
        return None
    text = " ".join([asset_id.replace("_", " "), str(item.get("name") or ""), *map(str, item.get("tags") or []),
                     *map(str, item.get("categories") or [])])
    hits = len(wanted & _words(text))
    if not hits:
        return None
    authors = ", ".join(map(str, (item.get("authors") or {}).keys()))[:NAME_MAX]
    return {"source": "polyhaven", "uid": asset_id, "name": str(item.get("name") or asset_id)[:NAME_MAX], "license": "CC0",
            "author": authors, "page": f"https://polyhaven.com/a/{asset_id}", "animations": 0, "faces": 50_000,
            "thumbnail": f"https://cdn.polyhaven.com/asset_img/thumbs/{asset_id}.png?width=512", "hits": hits}


async def search(query: str, english: str = "") -> list[dict]:
    wanted = _words(query) | _words(english)
    async with httpx.AsyncClient(timeout=fetch.TIMEOUT, follow_redirects=False) as client:
        response = await client.get(f"{API}/assets", params={"t": "models"})
        response.raise_for_status()
        assets = response.json()
    found = [_candidate(k, v, wanted) for k, v in assets.items() if isinstance(v, dict)] if isinstance(assets, dict) else []
    return sorted((c for c in found if c), key=lambda c: c["hits"], reverse=True)


async def download(uid: str) -> bytes:
    async with httpx.AsyncClient(timeout=fetch.TIMEOUT, follow_redirects=False) as client:
        response = await client.get(f"{API}/files/{uid}")
        response.raise_for_status()
        files = response.json()
    sizes = ((files.get("gltf") or {}) if isinstance(files, dict) else {})
    pick = sizes.get("2k") or sizes.get("1k") or {}
    entry = pick.get("gltf") or {}
    if not entry.get("url") or len(entry.get("include") or {}) > MAX_FILES:
        raise fetch.FetchError("holo_no_download")
    out = {"scene.gltf": await fetch.download(entry["url"])}
    for path, item in (entry.get("include") or {}).items():
        out[fetch.safe_name(path)] = await fetch.download(item.get("url", ""))
    return fetch.pack_files(out)
