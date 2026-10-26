import asyncio
import json
import logging
import re
import time

import httpx
from access import NO_CACHE, is_local, lang_of, require_admin, require_display
from background import queue as install_queue
from config import CORE_URL
from core_client import core
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from state import store
from tasks import background

from features.authz import resolve as authz_resolve
from features.authz.principal import act_as, acting
from features.places import context as place_context
from features.brain.brains import brains
from features.brain.residency import primary
from features.brain.trace import trace
from features.capabilities import manifest as capabilities
from features.chat import addressee, assistant, brain_chain, intents, speaker, streaming, voice_id, wake
from features.chat.dialogue import dialogue
from features.chat.journey_flow import ChatJourney
from features.chat.layout import presence
from features.chat.skills import ambient
from features.laws import guard
from features.laws.laws import laws
from features.mind.mind import mind
from features.chat import context as request_context
from features.desktop.desk import desk
from features.people import learning, people
from features.skills.library import library as skill_library
from features.study import study
from features.voices import languages
from features.voices.catalog import home_lang
from features.voices.downloads import ensure_language
from identity import assistant_name

log = logging.getLogger("nuxiva.chat")
public_routes = APIRouter()
admin_routes = APIRouter()

NL = chr(10)
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")


async def _core_call(query: str, device: str, speech_lang: dict) -> dict:
    present = [p["slug"] for p in store.presence.get("people", []) if p.get("known")]
    context = {"people_present": people.context_for(present)} if present else {}
    context["laws"] = laws.preamble()
    if capabilities.enabled():
        context["capabilities"] = capabilities.summary()
    context["speaker"] = speaker.instruction()
    recent = dialogue.context(device)
    if recent:
        context["dialogue"] = recent
    knowledge = await study.engine.recall(query)
    if knowledge:
        context["knowledge"] = knowledge
    long_term = mind.recall(query, who=acting().slug)
    if long_term:
        context["long_term"] = long_term
    route = await brains.route(query)
    route["lang"] = speech_lang["lang"]
    rule = languages.instruction(speech_lang["lang"], speech_lang["teach"])
    if rule:
        context["reply_language"] = rule

    async def core_local(models: list[str]) -> dict:
        payload = {"query": query, "device_id": device,
                   "context": {**context, "models": models, "max_tokens": route["max_tokens"],
                               "pinned": primary() or ""}}
        started = time.time()
        call = trace.begin("conversation", route["reason"], models)
        trace.attempt(call, models[0])
        try:
            if streaming.active():
                data = await streaming.core_stream(payload)
            else:
                r = await core.request("POST", "/api/v1/command", json=payload, timeout=240)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            trace.abort(call, str(exc) or type(exc).__name__)
            raise
        model = ((data.get("result_data") or {}).get("model") or "").removeprefix("ollama/")
        if model:
            brains.record(model, (time.time() - started) * 1000, model in models, route["kind"])
        if model and models and model != models[0]:
            trace.failed(call, models[0], "non disponibile")
        if not model:
            trace.note(call, f"gestita dall'agente {data.get('agent_id') or 'core'}")
        trace.finish(call, model, (time.time() - started) * 1000, data.get("speech_output") or "")
        if model:
            data["agent_id"] = f"{data.get('agent_id') or 'core'} · {model} ({brain_chain.engine_label(route.get('lang'))})"
        return data

    try:
        from loops import default_mode_network
        default_mode_network.record_activity()
    except (ImportError, AttributeError, RuntimeError) as exc:
        log.warning("Attività non registrata: %s", exc)
    try:
        return await brain_chain.ask(query, device, context, route, core_local)
    except brain_chain.NoBrainAvailable as exc:
        store.event("ERROR", f"Nessun cervello ha risposto: {exc}", "core")
        raise HTTPException(502, "Nessun cervello disponibile: controlla modelli locali e chiavi cloud")


def _heard(body: dict) -> dict:
    slug = str(body.get("speaker") or "")
    known = body.get("voice_known")
    return {"followup": bool(body.get("followup")), "speaker": slug if SLUG_RE.match(slug) else "",
            "voice_known": known if isinstance(known, bool) else None}


async def assistant_chat(text: str, device: str, heard_lang: str | None = None, heard: dict | None = None, internal: bool = False) -> JSONResponse:
    heard = heard or {}
    if not internal:
        install_queue.note_activity()
    text = (text or "").strip()
    if not text:
        raise HTTPException(400, "Messaggio vuoto")
    if len(text) > 4000:
        raise HTTPException(413, "Messaggio troppo lungo")
    if store.phase not in ("READY", "DEGRADED"):
        raise HTTPException(503, f"{assistant_name()} non è ancora operativa")
    if not internal:
        study.engine.activity("chat")
    request_context.device.set(device)
    request_context.voice.set(heard.get("speaker") or "")
    principal = authz_resolve.for_request(device, heard.get("speaker") or "", text)
    act_as(principal)
    room = place_context.enter(principal.slug, principal.source, device)
    if not internal and heard.get("speaker"):
        try:
            from nuxiva_bus import BusError, nuxiva_bus
            nuxiva_bus.publish("voice.speaker", {"speaker": heard["speaker"], "known": bool(heard.get("voice_known")), "device": device[:60]},
                               origin="voice")
        except (ImportError, BusError) as exc:
            log.warning("Evento del parlante non pubblicato: %s", exc)
    directed, confidence = True, 1.0
    if heard.get("followup"):
        verdict = addressee.judge(text, device)
        directed, confidence = verdict.directed, verdict.score
        if not verdict.directed:
            return JSONResponse({"ignored": True, "reason": verdict.reason, "score": verdict.score})
    said, text = text, dialogue.resolve(device, text)
    speech_lang = languages.resolve(text, device, heard_lang, principal.slug)
    if speech_lang["lang"] != home_lang():
        background(ensure_language(speech_lang["lang"]))

    async def core_call(query: str) -> dict:
        return await _core_call(query, device, speech_lang)

    flow = ChatJourney(said, text, device, heard.get("speaker") or "utente", internal=internal)
    enroll = voice_id.command(text)
    if guard.attempt(said) or guard.attempt(text):
        guard.record(said, device)
        flow.refused(guard.REFUSAL)
        result = {"reply": guard.REFUSAL, "intent": "laws", "agent": "leggi fondamentali", "elapsed_ms": 0}
    elif enroll:
        flow.enrolled(enroll[0])
        result = {"reply": enroll[0], "ui": enroll[1], "intent": "voice_id", "agent": "impronta vocale", "elapsed_ms": 0}
    else:
        flow.begin()
        if not internal:
            desk.request_started()
        try:
            result = await assistant.handle(text, core_call, speech_lang)
        except BaseException as exc:
            flow.failed(exc)
            raise
        flow.answered(result)
    result["reply"] = speaker.fix_address(result.get("reply") or "") + voice_id.offer(heard.get("voice_known"))
    if isinstance(result.get("ui"), dict):
        result["ui"].setdefault("presence", presence(result["reply"], result["ui"]))
    if not internal:
        dialogue.remember(device, said, result["reply"], result.get("intent", ""))
    result["lang"] = languages.detect(result.get("reply") or "", speech_lang["lang"])
    result["language"] = {**speech_lang, "label": languages.label(speech_lang["lang"])}
    result["identity"] = principal.describe()
    result["room"] = {"id": room.id, "name": room.name} if room else None
    if not internal:
        study.engine.note_query(text, result.get("intent", ""))
        desk.on_intent(result.get("intent", ""), result.get("ui") or {})
        if not str(result.get("agent", "")).startswith("algoritmo") and skill_library.needs_algorithm(text):
            background(skill_library.learn(text, brains.config()["deep"]))
        background(mind.evaluate(said, result.get("reply", ""), result.get("intent", ""), device, directed, confidence,
                                 (result.get("ui") or {}).get("mode", ""), str(result.get("agent", "")),
                                 heard.get("speaker") or ""))
        learner = heard.get("speaker") or principal.slug
        if directed and learner and people.load(learner):
            background(learning.observe_async(said, learner))
    return JSONResponse(result)


async def assistant_reply(text: str, device: str, lang: str | None = None) -> dict:
    return json.loads((await assistant_chat(text, device, lang)).body)


@public_routes.post("/api/assistant/chat")
async def public_chat(request: Request):
    require_display(request, f"Per parlare con {assistant_name()} da remoto accedi al pannello :8080")
    body = await request.json()
    internal = bool(body.get("internal") or request.headers.get("x-nuxiva-internal") == "1")
    device = "selftest" if internal else ("kiosk" if is_local(request) else "remote")
    return await assistant_chat(body.get("text", ""), device, lang_of(body),
                                _heard(body), internal=internal)


def _sse(event: dict) -> str:
    return "data: " + json.dumps(event, ensure_ascii=False) + NL + NL


async def _stream_chat(text: str, device: str, lang: str | None, heard: dict | None):
    queue: asyncio.Queue = asyncio.Queue()
    marker = streaming.sink.set(queue)
    try:
        task = asyncio.create_task(assistant_chat(text, device, lang, heard))
    finally:
        streaming.sink.reset(marker)
    while True:
        getter = asyncio.create_task(queue.get())
        done, _ = await asyncio.wait({getter, task}, return_when=asyncio.FIRST_COMPLETED)
        if getter in done:
            yield _sse(getter.result())
            continue
        getter.cancel()
        while not queue.empty():
            yield _sse(queue.get_nowait())
        break
    try:
        response = task.result()
    except HTTPException as exc:
        yield _sse({"type": "error", "status": exc.status_code, "detail": str(exc.detail)})
        return
    yield _sse({"type": "done", **json.loads(response.body)})


def _streaming_response(generator) -> StreamingResponse:
    return StreamingResponse(generator, media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@public_routes.post("/api/assistant/chat/stream")
async def public_chat_stream(request: Request):
    require_display(request, f"Per parlare con {assistant_name()} da remoto accedi al pannello :8080")
    body = await request.json()
    return _streaming_response(_stream_chat(body.get("text", ""), "kiosk" if is_local(request) else "remote", lang_of(body), _heard(body)))


@admin_routes.post("/api/assistant/chat/stream")
async def admin_chat_stream(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    return _streaming_response(_stream_chat(body.get("text", ""), "admin", lang_of(body), None))


@public_routes.get("/api/ambient")
async def public_ambient():
    return await ambient.current()


@public_routes.post("/api/assistant/wake")
async def public_wake(request: Request):
    require_display(request)
    request_context.device.set("kiosk" if is_local(request) else "remote")
    install_queue.note_activity()
    from features.automations.bus import emit
    emit("wake", {"device": request_context.device.get()})
    desk.wake()
    result = await wake.greeting(wake.wake_language())
    desk.show("g_notify", result["card"], key="wake", ttl=25)
    dialogue.remember(request_context.device.get(), assistant_name(), result["reply"], "wake")
    return result


@admin_routes.post("/api/assistant/chat")
async def admin_chat(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    return await assistant_chat(body.get("text", ""), "admin", lang_of(body))


@admin_routes.delete("/api/assistant/history")
async def admin_forget_history(user: str = Depends(require_admin)):
    from features.chat.history import history
    removed = history.forget()
    dialogue.turns.clear()
    dialogue.loaded.clear()
    store.event("INFO", f"Storia delle conversazioni cancellata da {user} ({removed} scambi)", "chat")
    return {"removed": removed}


@public_routes.post("/api/activity")
async def public_activity(request: Request):
    require_display(request)
    study.engine.activity("display")
    return {"ok": True}


@public_routes.get("/api/assistant/predict")
async def public_predict(q: str = ""):
    return intents.predict(q[:500])


@public_routes.get("/api/assistant/memory")
async def public_memory():
    try:
        r = await core.request("GET", "/api/v1/knowledge/graph", timeout=20)
        return JSONResponse(r.json().get("graph", {}), headers=NO_CACHE)
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, "Memoria non disponibile")


@public_routes.post("/api/v1/stream/reasoning")
@public_routes.get("/api/v1/stream/reasoning")
async def public_stream_reasoning(request: Request):
    if request.method == "POST":
        body = await request.json()
        query = body.get("query", "")
    else:
        query = request.query_params.get("query", "")

    async def event_stream():
        async with httpx.AsyncClient(timeout=None) as client:
            token = await core._token(client)
            headers = {"Authorization": f"Bearer {token}", "Accept": "text/event-stream"}
            async with client.stream("POST", f"{CORE_URL}/api/v1/stream/reasoning", json={"query": query}, headers=headers) as resp:
                async for line in resp.aiter_lines():
                    yield f"{line}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@public_routes.get("/api/assistant/mode")
async def get_assistant_mode(request: Request):
    from features.locale.api import page_language
    from server.core.reasoning.engines.scanner import engine_scanner
    lang = page_language(request, False)
    default_id = engine_scanner.get_default_engine().version.value
    active_mode = default_id
    engines = [eng.get_profile(is_active=eng.version.value == active_mode, lang=lang) for eng in engine_scanner.list_engines()]

    return {
        "mode": active_mode,
        "default": default_id,
        "modes": engines,
        "engines": engines,
    }


@public_routes.get("/api/assistant/mode/explain")
async def explain_assistant_mode(mode: str, request: Request):
    from features.chat import reasoning_explain
    from features.locale.api import page_language
    try:
        return JSONResponse(reasoning_explain.explain(mode, page_language(request, False)), headers=NO_CACHE)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except LookupError:
        raise HTTPException(404, "Motore non trovato")


