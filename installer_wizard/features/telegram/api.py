import json

from fastapi import APIRouter, Depends, HTTPException, Request

import updater
from access import require_admin
from features.chat.api import assistant_reply
from features.network.explorer import explorer
from features.people import connectors, people
from features.telegram.bot import bot
from features.vision.proxy import snapshot
from features.voices.synthesis import synthesize
from orchestrator import orch
from state import store
from tasks import background, delayed

admin_routes = APIRouter()


async def _stt(pcm: bytes) -> str:
    import websockets
    async with websockets.connect("ws://127.0.0.1:8093", max_size=2 ** 22) as ws:
        await ws.send(json.dumps({"type": "transcribe_start"}))
        for i in range(0, len(pcm), 32000):
            await ws.send(pcm[i:i + 32000])
        await ws.send(json.dumps({"type": "transcribe_end"}))
        async for message in ws:
            event = json.loads(message) if isinstance(message, str) else {}
            if event.get("type") == "transcription":
                return event.get("text", "")
    return ""


async def _update() -> str:
    info = await updater.check()
    if not info.get("available"):
        return f"✅ Nuxiva è aggiornata ({(info.get('local_rev') or '?')[:7]})."
    background(updater.apply("richiesto da Telegram"))
    return f"⬆️ Aggiornamento {info['local_rev'][:7]} → {(info.get('target_rev') or info['remote_rev'])[:7]} avviato: la avviso quando è pronto."


async def _repair() -> str:
    background(orch.converge(reason="Riparazione richiesta da Telegram"))
    return "🛠 Verifica e riparazione di tutti i componenti avviata."


bot.handlers.update(
    chat=assistant_reply, tts=synthesize, stt=_stt, snapshot=snapshot,
    reminders=lambda days: people.reminders(days), update=_update,
    bound=lambda slug, chat_id: people.update(slug, {"telegram_id": chat_id}), repair=_repair,
    reboot=lambda: delayed("systemctl", "reboot"),
    network=lambda: explorer.listing(),
)


def _person(slug: str) -> None:
    if not people.load(slug):
        raise HTTPException(404, "Persona non trovata")


connectors.register("telegram", "Telegram", "send", bot.person_status)


@admin_routes.get("/api/people/{slug}/telegram")
async def person_telegram(slug: str, _: str = Depends(require_admin)):
    _person(slug)
    return bot.person_status(slug)


@admin_routes.post("/api/people/{slug}/telegram/pair-code")
async def person_telegram_code(slug: str, user: str = Depends(require_admin)):
    _person(slug)
    if not bot.token:
        raise HTTPException(400, "Imposta prima il token del bot in Configurazione")
    store.event("INFO", f"Codice di abbinamento Telegram per {slug} generato da {user}", "telegram")
    return bot.new_pair_code(slug)


@admin_routes.put("/api/people/{slug}/telegram/{chat_id}")
async def person_telegram_chat(slug: str, chat_id: str, request: Request, _: str = Depends(require_admin)):
    _person(slug)
    if not any(chat["id"] == chat_id for chat in bot.chats_of(slug)):
        raise HTTPException(404, "Chat non abbinata a questa persona")
    body = await request.json()
    bot.update_chat(chat_id, {k: v for k, v in body.items() if k in ("notify", "voice")})
    return bot.person_status(slug)


@admin_routes.delete("/api/people/{slug}/telegram")
async def person_telegram_unlink(slug: str, user: str = Depends(require_admin)):
    _person(slug)
    removed = bot.unlink_person(slug)
    people.update(slug, {"telegram_id": ""})
    store.event("INFO", f"Telegram di {slug} scollegato da {user} ({removed} chat)", "telegram")
    return bot.person_status(slug)


@admin_routes.get("/api/telegram")
async def admin_telegram(_: str = Depends(require_admin)):
    return bot.summary()


@admin_routes.post("/api/telegram/pair-code")
async def admin_telegram_code(user: str = Depends(require_admin)):
    if not bot.token:
        raise HTTPException(400, "Imposta prima il token del bot in Configurazione")
    store.event("INFO", f"Codice di abbinamento Telegram generato da {user}", "telegram")
    return bot.new_pair_code()


@admin_routes.put("/api/telegram/chats/{chat_id}")
async def admin_telegram_chat(chat_id: str, request: Request, _: str = Depends(require_admin)):
    try:
        bot.update_chat(chat_id, await request.json())
    except KeyError:
        raise HTTPException(404, "Chat non abbinata")
    return {"ok": True}


@admin_routes.delete("/api/telegram/chats/{chat_id}")
async def admin_telegram_remove(chat_id: str, user: str = Depends(require_admin)):
    bot.remove_chat(chat_id)
    store.event("INFO", f"Chat Telegram {chat_id} rimossa da {user}", "telegram")
    return {"ok": True}
