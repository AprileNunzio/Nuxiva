import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from access import require_admin
from .service import VoiceLogService, VoiceLogUnavailable

routes = APIRouter(prefix="/voice", tags=["ai_studio"])
voice_log = VoiceLogService()
log = logging.getLogger("nuxiva.ai_studio")
NO_STORE = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}


class VoiceFeedbackRequest(BaseModel):
    verdict: str = Field("", pattern=r"^(|ok|wrong)$")
    correction: str = Field("", max_length=2000)
    note: str = Field("", max_length=600)


def _unavailable(exc: VoiceLogUnavailable) -> HTTPException:
    return HTTPException(status_code=503, detail=f"voice_log_unavailable: {str(exc)[:200]}")


def _audit_playback(entry_id: str) -> None:
    try:
        from agenti.sentinel import record as sentinel_record
    except ImportError as exc:
        log.warning("Audit dell'ascolto non disponibile: %s", exc)
        return
    sentinel_record.record("sentinel.read", sentinel_record.NUXIVA, "sentinel.audio_playback",
                           {"entry_id": entry_id, "origin": "ai_studio"}, "household", "ai_studio")


@routes.get("/turns")
async def list_turns(
    limit: int = Query(50, ge=1, le=200),
    before: float = Query(0.0, ge=0.0),
    channel: str = Query("voice", pattern=r"^(|voice|text)$"),
    q: str = Query("", max_length=120),
    _=Depends(require_admin),
) -> Dict[str, Any]:
    try:
        items = voice_log.list(limit, before, channel, q)
    except VoiceLogUnavailable as exc:
        raise _unavailable(exc)
    return {"items": items, "stats": voice_log.stats()}


@routes.get("/turns/{entry_id}/audio")
async def turn_audio(entry_id: str, _=Depends(require_admin)) -> Response:
    try:
        wav = voice_log.audio(entry_id)
    except VoiceLogUnavailable as exc:
        raise _unavailable(exc)
    if wav is None:
        raise HTTPException(status_code=404, detail="Recording not available")
    _audit_playback(entry_id)
    return Response(wav, media_type="audio/wav", headers=NO_STORE)


@routes.post("/turns/{entry_id}/feedback")
async def turn_feedback(entry_id: str, body: VoiceFeedbackRequest, _=Depends(require_admin)) -> Dict[str, bool]:
    try:
        saved = voice_log.feedback(entry_id, body.verdict, body.correction.strip(), body.note.strip())
    except VoiceLogUnavailable as exc:
        raise _unavailable(exc)
    if not saved:
        raise HTTPException(status_code=404, detail="Voice turn not linked to a recording")
    return {"ok": True}


@routes.delete("/turns/{entry_id}")
async def delete_turn(entry_id: str, _=Depends(require_admin)) -> Dict[str, bool]:
    try:
        removed = voice_log.delete(entry_id)
    except VoiceLogUnavailable as exc:
        raise _unavailable(exc)
    if not removed:
        raise HTTPException(status_code=404, detail="Voice turn not found")
    return {"ok": True}
