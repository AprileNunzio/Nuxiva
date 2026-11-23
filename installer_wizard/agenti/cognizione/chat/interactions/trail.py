import logging
import re
import sqlite3

from agenti.chat import addressee
from agenti.chat.interactions.store import REF, Interaction, interactions

DISPLAY_DEVICES = ("kiosk", "remote_display", "remote")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
log = logging.getLogger("nuxiva.chat")


def voice_ref(body: dict) -> str:
    ref = str(body.get("voice_ref") or "")
    return ref if REF.match(ref) else ""


def heard_from(body: dict) -> dict:
    slug = str(body.get("speaker") or "")
    known = body.get("voice_known")
    return {"followup": bool(body.get("followup")), "speaker": slug if SLUG_RE.match(slug) else "",
            "voice_known": known if isinstance(known, bool) else None,
            "same_speaker": addressee.flag(body.get("same_speaker")),
            "mixed_speakers": addressee.flag(body.get("mixed_speakers")),
            "voices_active": addressee.voices(body.get("voices_active")),
            "voice_ref": voice_ref(body)}


def heard_for(device: str, body: dict) -> dict | None:
    if device == "kiosk":
        return heard_from(body)
    ref = voice_ref(body)
    return {"voice_ref": ref} if ref else None


def record(device: str, said: str, resolved: str, result: dict, heard: dict | None, directed: bool = True,
           reason: str = "") -> str:
    if device not in DISPLAY_DEVICES:
        return ""
    heard = heard or {}
    ref = heard.get("voice_ref") or ""
    item = Interaction(device=device, channel="voice" if ref else "text", said=said or "",
                       resolved=resolved if resolved != said else "", reply=str(result.get("reply") or ""),
                       intent=str(result.get("intent") or ""), agent=str(result.get("agent") or ""),
                       lang=str(result.get("lang") or ""), elapsed_ms=int(result.get("elapsed_ms") or 0),
                       directed=directed, voice_ref=ref, speaker=str(heard.get("speaker") or ""),
                       score=float(result.get("score") or 0.0), reason=reason)
    try:
        return interactions.add(item)
    except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
        log.warning("Interazione della pagina 80 non registrata: %s", exc)
        return ""
