import asyncio
import re

import httpx

from config import env_get

from agenti.hands.holo.catalog import fetch

API = "https://api.meshy.ai/openapi/v2/text-to-3d"
POLL_SECONDS = 6
MAX_POLLS = 150
TASK_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")
TIMEOUT = httpx.Timeout(30.0)


def token() -> str:
    return env_get("NUXIVA_MESHY_TOKEN", "").strip()


def _headers() -> dict:
    return {"Authorization": f"Bearer {token()}"}


async def _task(task_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as client:
        response = await client.get(f"{API}/{task_id}", headers=_headers())
    if response.status_code != 200:
        raise fetch.FetchError(f"holo_http_{response.status_code}")
    data = response.json()
    if not isinstance(data, dict):
        raise fetch.FetchError("holo_bad_reply")
    return data


async def _run(body: dict, stage: str, notify) -> dict:
    created = await fetch.post_json(API, body, headers=_headers())
    task_id = str(created.get("result") or "")
    if not TASK_ID.match(task_id):
        raise fetch.FetchError("holo_bad_reply")
    for _ in range(MAX_POLLS):
        await asyncio.sleep(POLL_SECONDS)
        task = await _task(task_id)
        status = task.get("status")
        if status == "SUCCEEDED":
            return task
        if status in ("FAILED", "CANCELED"):
            raise fetch.FetchError("holo_cloud_failed")
        notify("forge_cloud", stage=stage, percent=max(0, min(100, int(task.get("progress") or 0))))
    raise TimeoutError("holo_cloud_timeout")


async def generate(prompt: str, notify) -> tuple[bytes, str]:
    if not token():
        raise fetch.FetchError("holo_cloud_token_missing")
    preview = await _run({"mode": "preview", "prompt": prompt[:800], "ai_model": "latest", "should_remesh": True,
                          "topology": "triangle", "target_polycount": 60000, "origin_at": "center"}, "shape", notify)
    preview_id = str(preview.get("id") or "")
    if not TASK_ID.match(preview_id):
        raise fetch.FetchError("holo_bad_reply")
    refined = await _run({"mode": "refine", "preview_task_id": preview_id, "enable_pbr": True, "texture_prompt": prompt[:800]},
                         "texture", notify)
    glb_url = str((refined.get("model_urls") or {}).get("glb") or "")
    thumbnail = str(refined.get("thumbnail_url") or "")
    blob = await fetch.download(glb_url)
    return blob, thumbnail if fetch.allowed(thumbnail) else ""
