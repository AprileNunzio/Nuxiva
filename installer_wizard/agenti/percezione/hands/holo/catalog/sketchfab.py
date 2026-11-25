import httpx

from config import env_get

from agenti.hands.holo.catalog import fetch

API = "https://api.sketchfab.com/v3"
RESULTS = 24
OPEN_LICENSES = ("cc0", "public domain", "attribution", "cc by", "cc-by")
CLOSED_LICENSES = ("standard", "editorial")
NAME_MAX = 96


def token() -> str:
    return env_get("NUXIVA_SKETCHFAB_TOKEN", "").strip()


def _license(item: dict) -> str:
    raw = item.get("license")
    if isinstance(raw, dict):
        raw = raw.get("label") or raw.get("slug") or ""
    return str(raw or "")[:NAME_MAX]


def _open(label: str) -> bool:
    low = label.lower()
    return any(k in low for k in OPEN_LICENSES) and not any(k in low for k in CLOSED_LICENSES)


def _thumbnail(item: dict) -> str:
    images = ((item.get("thumbnails") or {}).get("images")) or []
    usable = [i for i in images if isinstance(i, dict) and fetch.allowed(i.get("url", "")) and 400 <= int(i.get("width") or 0) <= 1280]
    return max(usable, key=lambda i: int(i.get("width") or 0))["url"] if usable else ""


def _candidate(item: dict) -> dict | None:
    uid = str(item.get("uid") or "")
    label = _license(item)
    if not uid.isalnum() or len(uid) > 64 or not item.get("isDownloadable") or not _open(label):
        return None
    user = item.get("user") or {}
    return {"source": "sketchfab", "uid": uid, "name": str(item.get("name") or "")[:NAME_MAX], "license": label,
            "author": str(user.get("displayName") or user.get("username") or "")[:NAME_MAX],
            "page": f"https://sketchfab.com/3d-models/{uid}", "animations": int(item.get("animationCount") or 0),
            "faces": int(item.get("faceCount") or 0), "thumbnail": _thumbnail(item)}


async def search(query: str) -> list[dict]:
    found: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=fetch.TIMEOUT, follow_redirects=False) as client:
        for animated in ("true", "false"):
            params = {"type": "models", "q": query[:80], "downloadable": "true", "animated": animated,
                      "count": str(RESULTS), "sort_by": "-likeCount"}
            response = await client.get(f"{API}/search", params=params)
            response.raise_for_status()
            for item in (response.json().get("results") or []):
                candidate = _candidate(item) if isinstance(item, dict) else None
                if candidate and candidate["uid"] not in found:
                    found[candidate["uid"]] = candidate
    return list(found.values())


async def download(uid: str) -> bytes:
    key = token()
    if not key:
        raise fetch.FetchError("holo_sketchfab_token_missing")
    headers = {"Authorization": f"Token {key}"}
    async with httpx.AsyncClient(timeout=fetch.TIMEOUT, follow_redirects=False) as client:
        response = await client.get(f"{API}/models/{uid}/download", headers=headers)
        response.raise_for_status()
        links = response.json()
    for flavour in ("glb", "gltf"):
        link = (links.get(flavour) or {}) if isinstance(links, dict) else {}
        url = link.get("url", "")
        if url and int(link.get("size") or 0) <= fetch.MAX_DOWNLOAD:
            return fetch.pack(await fetch.download(url))
    raise fetch.FetchError("holo_no_download")
