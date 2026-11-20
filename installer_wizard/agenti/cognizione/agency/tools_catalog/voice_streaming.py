import json

from agenti.agency.tools import Context, Tool, _text
from agenti.agency.voice_bridge import voice_governor


async def _voice_stream_dispatch(ctx: Context, args: dict) -> str:
    text = _text(args, "text", 2000)
    session_id = str(args.get("session_id") or "master_duplex").strip()
    context_kind = str(args.get("context_kind") or "normal").strip()

    sess = voice_governor.get_or_create(session_id)
    sess.adjust_pacing(context_kind)
    chunk_res = sess.on_llm_chunk(text)

    res = {
        "status": "voice_stream_dispatched",
        "session_id": session_id,
        "phase": sess.phase,
        "pacing_bpm": sess.pacing_bpm,
        "latency_ms": sess.latency_ms,
        "render_details": chunk_res,
    }
    return json.dumps(res, ensure_ascii=False)


async def _voice_barge_in_interrupt(ctx: Context, args: dict) -> str:
    session_id = str(args.get("session_id") or "master_duplex").strip()
    event_report = voice_governor.trigger_barge_in(session_id)

    res = {
        "status": "barge_in_executed",
        "session_id": session_id,
        "details": event_report,
        "holographic_orb_state": "pulsing_amber_interrupted",
    }
    return json.dumps(res, ensure_ascii=False)


TOOLS = {
    "voice_stream_dispatch": Tool(
        name="voice_stream_dispatch",
        description="Invia testo al sintetizzatore vocale full-duplex con modulazione di ritmo e tono a bassissima latenza.",
        args={"text": "string", "session_id": "optional string", "context_kind": "optional string"},
        capability="domain_task",
        run=_voice_stream_dispatch,
    ),
    "voice_barge_in_interrupt": Tool(
        name="voice_barge_in_interrupt",
        description="Interrompe istantaneamente la riproduzione vocale (< 150ms) quando l'utente inizia a parlare.",
        args={"session_id": "optional string"},
        capability="domain_task",
        run=_voice_barge_in_interrupt,
    ),
}
