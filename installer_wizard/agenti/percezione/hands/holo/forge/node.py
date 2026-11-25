import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

import httpx

from config import env_get

from agenti.hands.holo.catalog import fetch

TIMEOUT = httpx.Timeout(20.0, read=900.0)
STYLE = ", highly detailed, realistic proportions, physically based materials, single object, centered, no background, no ground"


class NodeBusy(RuntimeError):
    pass


def url() -> str:
    return env_get("NUXIVA_HOLO_GPU_URL", "").strip().rstrip("/")


def _safe_address(raw: str) -> bool:
    address = ipaddress.ip_address(raw.split("%", 1)[0])
    return (address.is_private or address.is_loopback) and not (address.is_link_local or address.is_multicast or address.is_unspecified)


def validated(base: str) -> str:
    parts = urlsplit(base)
    if parts.scheme not in ("http", "https") or parts.username or parts.password or not parts.hostname or parts.query or parts.fragment:
        raise fetch.FetchError("holo_gpu_bad_url")
    infos = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    if not infos or not all(_safe_address(info[4][0]) for info in infos):
        raise fetch.FetchError("holo_gpu_not_private")
    return base


def prompt(english: str) -> str:
    clean = " ".join("".join(c if c.isalnum() or c in " -'," else " " for c in english).split())[:200]
    return clean + STYLE


async def generate(english: str, seed: int) -> bytes:
    base = await asyncio.to_thread(validated, url())
    secret = env_get("NUXIVA_HOLO_GPU_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {secret}"} if secret else {}
    body = {"text": prompt(english), "texture": True, "octree_resolution": 256, "num_inference_steps": 30, "guidance_scale": 5.5,
            "face_count": 80000, "type": "glb", "seed": seed}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as client:
            async with client.stream("POST", f"{base}/generate", json=body, headers=headers) as response:
                if response.status_code in (429, 503):
                    raise NodeBusy("holo_gpu_busy")
                if response.status_code != 200:
                    raise fetch.FetchError(f"holo_http_{response.status_code}")
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > fetch.MAX_DOWNLOAD:
                        raise fetch.FetchError("holo_too_large")
                    chunks.append(chunk)
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        raise NodeBusy("holo_gpu_unreachable") from exc
    blob = b"".join(chunks)
    if blob[:4] != b"glTF":
        raise fetch.FetchError("holo_gpu_not_glb")
    return blob
