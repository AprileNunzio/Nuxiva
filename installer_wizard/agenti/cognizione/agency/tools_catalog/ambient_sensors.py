import json

from agenti.agency.ambient_fusion import PresenceSignal, ambient_fusion
from agenti.agency.tools import Context, Tool, _text


async def _ingest_ambient_presence(ctx: Context, args: dict) -> str:
    source_kind = _text(args, "source_kind", 60)
    detected_slug = args.get("detected_slug")
    confidence = float(args.get("confidence", 0.85))
    room_id = _text(args, "room_id", 80)

    sig = PresenceSignal(
        source_kind=source_kind,
        detected_slug=str(detected_slug).strip() if detected_slug else None,
        confidence=confidence,
        room_id=room_id,
    )
    res = ambient_fusion.ingest_presence_signal(sig)
    return json.dumps(res, ensure_ascii=False)


async def _get_ambient_room_state(ctx: Context, args: dict) -> str:
    room_id = _text(args, "room_id", 80)
    res = ambient_fusion.get_room_state(room_id)
    return json.dumps(res, ensure_ascii=False)


TOOLS = {
    "ingest_ambient_presence": Tool(
        name="ingest_ambient_presence",
        description="Elabora segnali di presenza biometrica continua (telecamere, microfoni, beacon) aggiornando gli occupanti della stanza e il ritmo circadiano.",
        args={"source_kind": "string", "detected_slug": "optional string", "confidence": "float", "room_id": "string"},
        capability="perceive",
        run=_ingest_ambient_presence,
    ),
    "get_ambient_room_state": Tool(
        name="get_ambient_room_state",
        description="Restituisce lo stato ambientale completo di una stanza (occupanti correnti, persona dominante, metriche sensori, contesto circadiano).",
        args={"room_id": "string"},
        capability="read",
        run=_get_ambient_room_state,
    ),
}
