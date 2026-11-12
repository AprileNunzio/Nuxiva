import asyncio
from fastapi import APIRouter, HTTPException, Request

from agenti.chat.reflex_engine import reflex_engine
from agenti.chat.reflex_memory import PersonaProfile, reflex_memory

router = APIRouter()
_barge_in_events: dict[str, asyncio.Event] = {}


@router.post("/api/chat/reflex")
async def chat_reflex(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    query = str(body.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query richiesta")
    user_name = body.get("user_name")
    lang = str(body.get("lang") or "it").strip()
    try:
        from agenti.sentinel.collectors.voice import record_voice
        record_voice(query, speaker_slug=user_name, recognized=bool(user_name and user_name != "user"), device="reflex")
    except Exception:
        pass
    response = reflex_engine.evaluate(query, user_name=user_name, lang=lang)
    return response.to_dict()


@router.get("/api/chat/persona")
async def get_persona(user_name: str | None = None):
    profile = reflex_memory.get_profile(user_name)
    if not profile:
        raise HTTPException(status_code=404, detail="Profilo utente non trovato")
    return profile.to_dict()


@router.post("/api/chat/persona")
async def update_persona(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Payload JSON non valido")
    user_name = str(body.get("user_name") or "user").strip()
    style = str(body.get("style") or "conversational").strip()
    interests = [str(i).strip() for i in body.get("interests", []) if str(i).strip()]
    facts = {str(k): str(v) for k, v in (body.get("facts") or {}).items()}
    profile = PersonaProfile(
        user_name=user_name,
        style=style,
        interests=interests,
        facts=facts,
    )
    reflex_memory.save_profile(profile)
    return profile.to_dict()


@router.post("/api/chat/learn")
async def learn_speech(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    utterance = str(body.get("utterance") or "").strip()
    if not utterance:
        raise HTTPException(status_code=400, detail="Utterance richiesta")
    user_name = body.get("user_name")
    profile = reflex_memory.learn(utterance, user_name=user_name)
    return profile.to_dict()


@router.post("/api/chat/barge_in")
async def register_barge_in(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    session_id = str(body.get("session_id") or "default").strip()
    event = _barge_in_events.get(session_id)
    if event:
        event.set()
    else:
        new_ev = asyncio.Event()
        new_ev.set()
        _barge_in_events[session_id] = new_ev
    return {"status": "interrupted", "session_id": session_id}
