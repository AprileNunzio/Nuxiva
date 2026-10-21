import base64
import binascii

from server.features.repair_workbench.errors import InvalidFrameException

MAX_FRAME_BYTES = 4_500_000
_SIGNATURES = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")


def decode_frame(frame_base64: str) -> bytes:
    payload = frame_base64.split(",", 1)[1] if frame_base64.startswith("data:") else frame_base64
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidFrameException("encoding") from exc
    if len(raw) > MAX_FRAME_BYTES:
        raise InvalidFrameException("size")
    if not raw.startswith(_SIGNATURES):
        raise InvalidFrameException("format")
    return raw
