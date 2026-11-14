import hashlib
import json

from access import require_admin
from config import STATE_DIR
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from agenti.nodes.audit import audit
from agenti.nodes.inbox import inbox
from agenti.nodes.registry import registry

FIRMWARE_DIR = STATE_DIR / "firmware" / "esp32"
MAX_IMAGE = 3 * 1024 * 1024
MAX_PULSE_MS = 10000
MIN_PULSE_MS = 50
MAX_ON_MS = 24 * 3600 * 1000
RELAY_CHANNELS = 8
STATES = ("on", "off", "pulse")

public_routes = APIRouter()
admin_routes = APIRouter()


def relay_action(body: dict) -> dict:
    channel, state, ms = body.get("channel"), body.get("state"), body.get("ms")
    if not isinstance(channel, int) or isinstance(channel, bool) or not 0 <= channel < RELAY_CHANNELS:
        raise ValueError("esp32.relay.channel")
    if state not in STATES:
        raise ValueError("esp32.relay.state")
    action = {"type": "relay", "channel": channel, "state": state}
    if state == "pulse":
        if not isinstance(ms, int) or isinstance(ms, bool) or not MIN_PULSE_MS <= ms <= MAX_PULSE_MS:
            raise ValueError("esp32.relay.duration")
        action["ms"] = ms
    elif state == "on" and ms is not None:
        if not isinstance(ms, int) or isinstance(ms, bool) or not 0 <= ms <= MAX_ON_MS:
            raise ValueError("esp32.relay.duration")
        action["ms"] = ms
    return action


async def _json(request: Request, limit: int) -> dict:
    if int(request.headers.get("content-length") or 0) > limit:
        raise HTTPException(413, "payload_too_large")
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "invalid_request")
    if not isinstance(body, dict):
        raise HTTPException(400, "invalid_request")
    return body


def _authenticate(request: Request) -> dict:
    token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    try:
        return registry.authenticate(request.headers.get("x-nuxiva-node", ""), token)
    except PermissionError:
        raise HTTPException(401, "node.error.unauthorized")


@admin_routes.post("/api/nodes/{node_id}/relay")
async def node_relay(node_id: str, request: Request, user: str = Depends(require_admin)):
    node = registry.data["nodes"].get(node_id)
    if node is None or node.get("type") != "esp32":
        raise HTTPException(404, "node.error.not_found")
    try:
        action = relay_action(await _json(request, 512))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if "relay" not in (node.get("capabilities") or []):
        audit.record("node", node_id, "relay.deny", "capability")
        raise HTTPException(409, "esp32.relay.unsupported")
    audit.record("node", node_id, "relay", f"{action['channel']}:{action['state']}:{user}")
    inbox.push(node_id, action)
    return {"queued": True}


def load_firmware() -> tuple[dict, bytes]:
    try:
        manifest = json.loads((FIRMWARE_DIR / "manifest.json").read_text(encoding="ascii"))
        image = (FIRMWARE_DIR / "image.bin").read_bytes()
    except (OSError, ValueError):
        raise HTTPException(404, "esp32.firmware.missing")
    if not isinstance(manifest, dict) or len(image) > MAX_IMAGE:
        raise HTTPException(404, "esp32.firmware.missing")
    if manifest.get("size") != len(image) or manifest.get("sha256") != hashlib.sha256(image).hexdigest():
        raise HTTPException(409, "esp32.firmware.mismatch")
    return manifest, image


@public_routes.post("/api/nodes/firmware/esp32/manifest")
async def firmware_manifest(request: Request):
    _authenticate(request)
    manifest, _ = load_firmware()
    return Response(json.dumps(manifest, separators=(",", ":")), media_type="application/json",
                    headers={"Cache-Control": "no-store"})


@public_routes.post("/api/nodes/firmware/esp32/image")
async def firmware_image(request: Request):
    _authenticate(request)
    _, image = load_firmware()
    return Response(image, media_type="application/octet-stream", headers={"Cache-Control": "no-store"})
