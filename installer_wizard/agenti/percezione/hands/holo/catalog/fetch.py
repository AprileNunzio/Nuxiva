import base64
import io
import json
import posixpath
import struct
import zipfile
from urllib.parse import urlsplit

import httpx

ALLOWED_HOSTS = ("api.sketchfab.com", "media.sketchfab.com", "sketchfab-prod-media.s3.amazonaws.com", "api.polyhaven.com",
                 "dl.polyhaven.org", "cdn.polyhaven.com", "pubchem.ncbi.nlm.nih.gov", "files.rcsb.org", "search.rcsb.org",
                 "api.meshy.ai", "assets.meshy.ai")
MAX_DOWNLOAD = 96 * 1024 * 1024
MAX_UNZIPPED = 256 * 1024 * 1024
MAX_THUMB = 3 * 1024 * 1024
MAX_ENTRIES = 512
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
TIMEOUT = httpx.Timeout(30.0, read=120.0)


class FetchError(ValueError):
    pass


def allowed(url: str) -> bool:
    parts = urlsplit(str(url or ""))
    host = (parts.hostname or "").lower()
    return parts.scheme == "https" and not parts.username and parts.port in (None, 443) and host in ALLOWED_HOSTS


async def download(url: str, limit: int = MAX_DOWNLOAD, headers: dict | None = None) -> bytes:
    if not allowed(url):
        raise FetchError("holo_host_not_allowed")
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as client:
        async with client.stream("GET", url, headers=headers or {}) as response:
            if response.status_code != 200:
                raise FetchError(f"holo_http_{response.status_code}")
            declared = int(response.headers.get("content-length") or 0)
            if declared > limit:
                raise FetchError("holo_too_large")
            chunks, size = [], 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > limit:
                    raise FetchError("holo_too_large")
                chunks.append(chunk)
    return b"".join(chunks)


async def post_json(url: str, body: dict, limit: int = 1024 * 1024, headers: dict | None = None) -> dict:
    if not allowed(url):
        raise FetchError("holo_host_not_allowed")
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as client:
        response = await client.post(url, json=body, headers=headers or {})
    if response.status_code not in (200, 202):
        raise FetchError(f"holo_http_{response.status_code}")
    if len(response.content) > limit:
        raise FetchError("holo_too_large")
    data = response.json()
    if not isinstance(data, dict):
        raise FetchError("holo_bad_reply")
    return data


def safe_name(name: str) -> str:
    clean = posixpath.normpath(name.replace("\\", "/"))
    if clean.startswith(("/", "../")) or clean == ".." or "\x00" in clean:
        raise FetchError("holo_bad_archive")
    return clean


def _read_archive(blob: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ENTRIES or sum(i.file_size for i in infos) > MAX_UNZIPPED:
            raise FetchError("holo_bad_archive")
        return {safe_name(i.filename): archive.read(i) for i in infos if not i.is_dir()}


def _resource(files: dict[str, bytes], base: str, uri: str) -> bytes:
    if uri.startswith("data:"):
        return base64.b64decode(uri.split(",", 1)[1], validate=False)
    from urllib.parse import unquote
    key = safe_name(posixpath.join(base, unquote(uri)))
    if key not in files:
        raise FetchError("holo_missing_resource")
    return files[key]


def _pad(data: bytes, fill: bytes = b"\0") -> bytes:
    return data + fill * (-len(data) % 4)


def pack(blob: bytes) -> bytes:
    if blob[:4] == b"glTF":
        return blob
    return pack_files(_read_archive(blob))


def pack_files(files: dict[str, bytes]) -> bytes:
    scene = next((name for name in files if name.endswith(".gltf")), None)
    if scene is None:
        raise FetchError("holo_no_gltf")
    gltf = json.loads(files[scene])
    base = posixpath.dirname(scene)
    binary, offsets = b"", []
    for buffer in gltf.get("buffers") or []:
        offsets.append(len(binary))
        binary += _pad(_resource(files, base, buffer.get("uri", "")))
    for view in gltf.get("bufferViews") or []:
        view["byteOffset"] = int(view.get("byteOffset", 0)) + offsets[int(view.get("buffer", 0))]
        view["buffer"] = 0
    views = gltf.setdefault("bufferViews", [])
    for image in gltf.get("images") or []:
        uri = image.pop("uri", None)
        if uri is None:
            continue
        data = _resource(files, base, uri)
        ext = posixpath.splitext(uri.split("?")[0])[1].lower()
        image["mimeType"] = image.get("mimeType") or MIME.get(ext, "image/png")
        views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(data)})
        image["bufferView"] = len(views) - 1
        binary += _pad(data)
    gltf["buffers"] = [{"byteLength": len(binary)}]
    text = _pad(json.dumps(gltf, separators=(",", ":")).encode(), b" ")
    total = 12 + 8 + len(text) + 8 + len(binary)
    if total > MAX_DOWNLOAD:
        raise FetchError("holo_too_large")
    return (b"glTF" + struct.pack("<II", 2, total) + struct.pack("<I", len(text)) + b"JSON" + text
            + struct.pack("<I", len(binary)) + b"BIN\0" + binary)
