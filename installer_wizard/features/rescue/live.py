import logging

import httpx

from features.people import people
from features.redalert.service import redalert
from features.rescue.channels import Dispatcher
from features.rescue.coordinator import coordinator
from features.rescue.ear_link import EarLink
from features.sentinel import record
from features.telegram.bot import bot

log = logging.getLogger("nuxiva.rescue.live")
SEND_TIMEOUT = 15
AUDIT = {"delivery": "system.alert", "unreachable": "system.alert", "acknowledged": "system.recovered"}


class TelegramChannel:
    def __init__(self, client) -> None:
        self.client = client

    def chats(self, slug: str) -> list[str]:
        return [str(c["id"]) for c in self.client.chats_of(slug)] if self.client.token else []

    def owners(self) -> list[str]:
        if not self.client.token:
            return []
        return [str(k) for k, v in self.client.data.get("chats", {}).items() if v.get("role") == "owner"]

    async def send(self, chat_id: str, text: str, buttons: list | None) -> int | None:
        if not self.client.token:
            return None
        extra = {"reply_markup": {"inline_keyboard": buttons}} if buttons else {}
        try:
            result = await self.client.call("sendMessage", timeout=SEND_TIMEOUT, chat_id=chat_id, text=text[:4000],
                                            parse_mode="HTML", **extra)
        except (httpx.HTTPError, RuntimeError, ValueError) as exc:
            log.warning("Avviso di soccorso non consegnato a %s: %s", chat_id, exc)
            return None
        message_id = result.get("message_id") if isinstance(result, dict) else None
        return message_id if isinstance(message_id, int) and not isinstance(message_id, bool) else None

    async def clear(self, chat_id: str, message_id: int) -> None:
        if not self.client.token:
            return
        try:
            await self.client.call("editMessageReplyMarkup", timeout=SEND_TIMEOUT, chat_id=chat_id,
                                   message_id=message_id, reply_markup={"inline_keyboard": []})
        except (httpx.HTTPError, RuntimeError, ValueError) as exc:
            log.debug("Pulsanti di soccorso non rimossi: %s", exc)


class Alarm:
    def trigger(self, message: str) -> None:
        try:
            if not redalert.trigger(message):
                log.warning("Allarme in casa disattivato: avviso vocale di soccorso non diffuso")
        except RuntimeError as exc:
            log.error("Allarme in casa non avviato: %s", exc)

    def stop(self) -> None:
        redalert.stop()


def audit(kind: str, incident, params: dict) -> None:
    category = AUDIT.get(kind)
    if category is None:
        return
    record.record(category, record.NUXIVA, f"sentinel.rescue.{kind}", params, "sensitive", "rescue")


def profiles() -> list[dict]:
    return people.all_profiles(light=True)


async def _ear(message: dict) -> bool:
    sent = await link.send(message)
    if not sent:
        log.warning("Schermi e ascolto non raggiungibili per il messaggio di soccorso %s", message.get("type"))
    return sent


dispatcher = Dispatcher(coordinator, TelegramChannel(bot), _ear, Alarm(), profiles, audit)
link = EarLink(coordinator, dispatcher)
if dispatcher.submit not in coordinator.listeners:
    coordinator.listeners.append(dispatcher.submit)
bot.handlers["rescue"] = dispatcher.callback
