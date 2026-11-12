import asyncio
import json
import logging
import re
import time

import httpx
from access import NO_CACHE, is_local, lang_of, require_admin, require_display, session_user
from background import queue as install_queue
from config import CORE_URL
from core_client import core
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from state import store
from tasks import background

from agenti.authz import resolve as authz_resolve
from agenti.authz.access_control import account, allows
from agenti.authz.principal import act_as, acting
from agenti.places import context as place_context
from agenti.brain.brains import brains
from agenti.brain.residency import primary
from agenti.brain.trace import trace
from agenti.capabilities import manifest as capabilities
from agenti.chat import addressee, assistant, brain_chain, intents, speaker, streaming, turns, voice_id, wake
from agenti.chat.dialogue import dialogue
from agenti.chat.journey_flow import ChatJourney
from agenti.sentinel.collectors import operations
from agenti.chat.layout import presence
from agenti.chat.skills import ambient
from agenti.laws import guard
from agenti.laws.laws import laws
from agenti.mind.mind import mind
from agenti.chat import context as request_context
from agenti.desktop.desk import desk
from agenti.desktop.display_scope import is_host_display
from agenti.people import learning, people
from agenti.people.identity import first_name
from agenti.skills.library import library as skill_library
from agenti.study import study
from agenti.voices import languages
from agenti.voices.catalog import home_lang
from agenti.voices.downloads import ensure_language
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
    recent = dialogue.context(device, query)
    if recent:
        context["dialogue"] = recent
    knowledge = await study.engine.recall(query)
    if knowledge:
        context["knowledge"] = knowledge
    long_term = mind.recall(query, who=acting().slug)
    if long_term:
        context["long_term"] = long_term
    from agenti.chat.reflex_memory import reflex_memory
    prof = reflex_memory.learn(query)
    if prof and (prof.interests or prof.facts or (prof.user_name and prof.user_name != "user")):
        context["persona_memory"] = {
            "user_name": prof.user_name if prof.user_name != "user" else None,
            "style": prof.style,
            "interests": prof.interests,
            "facts": prof.facts,
        }
    route = await brains.route(query)
    route["lang"] = speech_lang["lang"]
    route["person"] = acting().slug if acting().role != "system" else ""
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
        if str(exc).startswith("privacy_blocked"):
            store.event("WARN", f"Richiesta trattenuta dalla privacy del Cervello: {exc}", "core")
            raise HTTPException(503, "privacy_blocked") from exc
        store.event("ERROR", f"Nessun cervello ha risposto: {exc}", "core")
        raise HTTPException(502, "Nessun cervello disponibile: controlla modelli locali e chiavi cloud")


def _speaker_name(slug: str) -> str:
    profile = people.load(slug) if slug and SLUG_RE.match(slug) else None
    return first_name(profile) if profile else ""


def _heard(body: dict) -> dict:
    slug = str(body.get("speaker") or "")
    known = body.get("voice_known")
    voices = body.get("voices_active")
    return {"followup": bool(body.get("followup")), "speaker": slug if SLUG_RE.match(slug) else "",
            "voice_known": known if isinstance(known, bool) else None,
            "same_speaker": addressee.flag(body.get("same_speaker")),
            "mixed_speakers": addressee.flag(body.get("mixed_speakers")),
            "voices_active": addressee.voices(voices)}


async def assistant_chat(text: str, device: str, heard_lang: str | None = None, heard: dict | None = None, internal: bool = False, client_id: str = "") -> JSONResponse:
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
        verdict = addressee.judge(text, device, heard)
        directed, confidence = verdict.directed, verdict.score
        if not verdict.directed:
            return JSONResponse({"ignored": True, "reason": verdict.reason, "score": verdict.score})
    said, text = text, dialogue.resolve(device, text)
    try:
        from agenti.sentinel.collectors.voice import record_voice
        record_voice(said or text, speaker_slug=principal.slug if principal else None,
                     recognized=bool(principal and principal.slug and principal.role != "system"),
                     device=device)
    except Exception:
        pass
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
        turn_id = flow.tracker.id if flow.tracker else ""
        with turns.running(turn_id) as turn:
            try:
                result = await assistant.handle(text, core_call, speech_lang)
            except asyncio.CancelledError:
                flow.cancelled()
                if turn and turn.stopping:
                    return JSONResponse({"cancelled": True})
                raise
            except Exception as exc:
                flow.failed(exc)
                operations.chat(device, turn_id, {"error": type(exc).__name__})
                raise
            if turn and turn.stopping:
                flow.cancelled()
                return JSONResponse({"cancelled": True})
        flow.answered(result)
    if not result.pop("exact_reply", False):
        result["reply"] = speaker.fix_address(result.get("reply") or "") + voice_id.offer(heard.get("voice_known"))
    operations.chat(device, flow.tracker.id if flow.tracker else "", result)
    if isinstance(result.get("ui"), dict):
        result["ui"].setdefault("presence", presence(result["reply"], result["ui"]))
    if not internal:
        dialogue.remember(device, said, result["reply"], result.get("intent", ""), _speaker_name(heard.get("speaker") or ""))
    result["lang"] = languages.detect(result.get("reply") or "", speech_lang["lang"])
    result["language"] = {**speech_lang, "label": languages.label(speech_lang["lang"])}
    result["identity"] = principal.describe()
    result["room"] = {"id": room.id, "name": room.name} if room else None
    if not internal:
        study.engine.note_query(text, result.get("intent", ""))
        cid = client_id or device
        desk.on_intent(result.get("intent", ""), result.get("ui") or {}, client_id=cid)
        store.live_dialogue = {
            "id": f"dlg_{int(time.time() * 1000)}",
            "user_text": said,
            "reply": result.get("reply", ""),
            "intent": result.get("intent", ""),
            "device": device,
            "client_id": cid,
            "speaker_slug": principal.slug,
            "mode": (result.get("ui") or {}).get("mode", "face"),
            "ts": time.time(),
        }
        if principal.slug:
            try:
                from agenti.desktop.presence_bridge import bridge
                bridge.update()
            except Exception:
                pass
        store.touch()
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


def _display_chat_device(request: Request) -> str:
    if is_host_display(request):
        return "kiosk"
    user = session_user(request) if request.url.scheme == "https" else None
    if user and allows(account(user)["role"], "api.admin"):
        return "remote"
    return "remote_display"


@public_routes.post("/api/assistant/chat")
async def public_chat(request: Request):
    require_display(request, f"Per parlare con {assistant_name()} da remoto accedi al pannello :8080")
    body = await request.json()
    device = _display_chat_device(request)
    internal = device == "kiosk" and request.headers.get("x-nuxiva-internal") == "1"
    cid = str(body.get("client_id") or request.headers.get("x-nuxiva-client") or device)[:80]
    request_context.client.set(cid)
    turns.owner.set(turns.request_owner(request))
    return await assistant_chat(body.get("text", ""), "selftest" if internal else device, lang_of(body),
                                _heard(body) if device == "kiosk" else None, internal=internal, client_id=cid)


def _sse(event: dict) -> str:
    return "data: " + json.dumps(event, ensure_ascii=False) + NL + NL


async def _stream_chat(text: str, device: str, lang: str | None, heard: dict | None, client_id: str = "",
                       owner: tuple[str, str] | None = None):
    if client_id:
        request_context.client.set(client_id)
    queue: asyncio.Queue = asyncio.Queue()
    marker = streaming.sink.set(queue)
    principal = turns.owner.set(owner)
    try:
        task = asyncio.create_task(assistant_chat(text, device, lang, heard))
    finally:
        streaming.sink.reset(marker)
        turns.owner.reset(principal)
    getter = None
    try:
        while not task.done():
            getter = asyncio.create_task(queue.get())
            done, _ = await asyncio.wait({getter, task}, return_when=asyncio.FIRST_COMPLETED)
            if task not in done:
                yield _sse(getter.result())
        if getter and not getter.done():
            getter.cancel()
        response = task.result()
        payload = json.loads(response.body)
        if not payload.get("cancelled"):
            if getter and getter in done and task in done:
                yield _sse(getter.result())
            while not queue.empty():
                yield _sse(queue.get_nowait())
        yield _sse({"type": "done", **payload})
    except HTTPException as exc:
        yield _sse({"type": "error", "status": exc.status_code, "detail": str(exc.detail)})
    finally:
        if getter and not getter.done():
            getter.cancel()
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


def _streaming_response(generator) -> StreamingResponse:
    return StreamingResponse(generator, media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@public_routes.post("/api/assistant/chat/stream")
async def public_chat_stream(request: Request):
    require_display(request, f"Per parlare con {assistant_name()} da remoto accedi al pannello :8080")
    body = await request.json()
    device = _display_chat_device(request)
    cid = str(body.get("client_id") or request.headers.get("x-nuxiva-client") or device)[:80]
    heard = _heard(body) if device == "kiosk" else None
    return _streaming_response(_stream_chat(body.get("text", ""), device, lang_of(body), heard,
                                           client_id=cid, owner=turns.request_owner(request)))


@admin_routes.post("/api/assistant/chat/stream")
async def admin_chat_stream(request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    cid = str(body.get("client_id") or request.headers.get("x-nuxiva-client") or "admin")[:80]
    return _streaming_response(_stream_chat(body.get("text", ""), "admin", lang_of(body), None,
                                           client_id=cid, owner=("user", user)))


@public_routes.get("/api/ambient")
async def public_ambient():
    return await ambient.current()


@public_routes.post("/api/assistant/wake")
async def public_wake(request: Request):
    require_display(request)
    dev = "kiosk" if is_local(request) else "remote"
    request_context.device.set(dev)
    install_queue.note_activity()
    from agenti.automations.bus import emit
    emit("wake", {"device": dev})
    desk.wake()
    result = await wake.greeting(wake.wake_language())
    cid = "kiosk" if is_local(request) else "remote"
    desk.show("g_notify", result["card"], key="wake", ttl=25, client_id=cid)
    dialogue.remember(dev, assistant_name(), result["reply"], "wake")
    store.live_dialogue = {
        "id": f"dlg_{int(time.time() * 1000)}",
        "user_text": "",
        "reply": result["reply"],
        "intent": "wake",
        "device": dev,
        "client_id": cid,
        "mode": "face",
        "ts": time.time(),
    }
    store.touch()
    return result


@admin_routes.post("/api/assistant/chat")
async def admin_chat(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    cid = str(body.get("client_id") or request.headers.get("x-nuxiva-client") or "admin")[:80]
    request_context.client.set(cid)
    return await assistant_chat(body.get("text", ""), "admin", lang_of(body), client_id=cid)


@admin_routes.delete("/api/assistant/history")
async def admin_forget_history(user: str = Depends(require_admin)):
    from agenti.chat.history import history
    removed = history.forget()
    dialogue.forget()
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
    from agenti.locale.api import page_language
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
    from agenti.chat import reasoning_explain
    from agenti.locale.api import page_language
    try:
        return JSONResponse(reasoning_explain.explain(mode, page_language(request, False)), headers=NO_CACHE)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except LookupError:
        raise HTTPException(404, "Motore non trovato")


from agenti.chat.reflex_routes import router as reflex_router
public_routes.include_router(reflex_router)



