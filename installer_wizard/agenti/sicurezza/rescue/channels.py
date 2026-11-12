import asyncio
import html
import logging
import secrets
import time
from collections import deque

from agenti.rescue import contacts
from agenti.rescue.text import emergency_number, translate

log = logging.getLogger("nuxiva.rescue.channels")
SUBJECT_TTL = 300.0
MAX_OUTBOX = 256
MAX_RETRIES = 4
RETRY_S = (5.0, 15.0, 30.0, 60.0)
CALLBACK = "rescue"


class Incident:
    def __init__(self, number: int, hazard: str | None, subject: str | None) -> None:
        self.number = number
        self.hazard = hazard or "medical"
        self.subject = subject
        self.token = secrets.token_hex(8)
        self.recipients: dict[str, dict] = {}
        self.retry: list[dict] = []
        self.acked_by = ""
        self.closed = False


class Dispatcher:
    def __init__(self, coordinator, telegram, ear, alarm, profiles, audit=None, clock=time.time) -> None:
        self.coordinator = coordinator
        self.telegram = telegram
        self.ear = ear
        self.alarm = alarm
        self.profiles = profiles
        self.audit = audit or (lambda *a, **k: None)
        self.clock = clock
        self.outbox: deque = deque(maxlen=MAX_OUTBOX)
        self.incident: Incident | None = None
        self.subject: tuple[str, float] | None = None
        self._lock: asyncio.Lock | None = None

    def note_subject(self, slug: str, now: float) -> None:
        if contacts.SLUG.match(slug or ""):
            self.subject = (slug, now)
            if self.incident and not self.incident.closed and self.incident.subject is None:
                self.incident.subject = slug

    def _subject(self, now: float) -> str | None:
        if self.subject and now - self.subject[1] <= SUBJECT_TTL:
            return self.subject[0]
        return None

    def submit(self, actions: list[dict], step: dict) -> None:
        if not actions:
            return
        meta = {"incident": int(step.get("incident") or 0), "hazard": step.get("hazard"), "at": float(step.get("at") or self.clock())}
        for action in actions:
            self.outbox.append((dict(action), meta))
        try:
            asyncio.get_running_loop().create_task(self.flush())
        except RuntimeError:
            return

    async def flush(self) -> None:
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            while self.outbox:
                action, meta = self.outbox.popleft()
                try:
                    await self._do(action, meta)
                except Exception:
                    log.exception("Azione di soccorso %s non eseguita", action.get("type"))
            await self._retry()

    def _current(self, meta: dict, hazard: str | None) -> Incident:
        if self.incident is None or self.incident.number != meta["incident"] or self.incident.closed:
            self.incident = Incident(meta["incident"], hazard or meta.get("hazard"), self._subject(meta["at"]))
        return self.incident

    def _levels(self, incident: Incident) -> list[list[str]]:
        tiers = int(self.coordinator.rescue.policy().get("family_tiers", 2))
        return contacts.plan(self.profiles(), incident.subject, tiers)

    def _names(self) -> dict[str, dict]:
        return {p.get("slug"): p for p in self.profiles() if isinstance(p, dict)}

    async def _do(self, action: dict, meta: dict) -> None:
        kind = action.get("type")
        hazard = str(action.get("hazard") or meta.get("hazard") or "medical")
        if kind == "ask_person":
            incident = self._current(meta, hazard)
            seconds = float(self.coordinator.rescue.policy().get("check_in_s", 30.0))
            await self.ear({"type": "rescue_ask", "hazard": hazard, "tone": action.get("tone", "spoken"),
                            "seconds": seconds, "number": emergency_number()})
            self.audit("ask", incident, {})
        elif kind == "alert_family":
            incident = self._current(meta, hazard)
            levels = self._levels(incident)
            tier = max(0, min(int(action.get("tier", 0)), len(levels) - 1))
            await self._alert(incident, levels[tier], tier, "alert_family", {})
        elif kind == "alert_emergency_contacts":
            incident = self._current(meta, hazard)
            rnd = int(action.get("round", 1))
            await self._alert(incident, contacts.everyone(self._levels(incident)), 100 + rnd, "alert_emergency",
                              {"round": rnd})
        elif kind == "remind_emergency_number":
            await self.ear({"type": "rescue_remind", "hazard": hazard, "number": emergency_number()})
        elif kind == "home_alarm":
            self.alarm.trigger(translate("home_alarm"))
        elif kind == "acknowledged":
            await self._acknowledged(int(action.get("tier", 0)))
        elif kind == "stand_down":
            await self._stand_down()

    def _message(self, key: str, incident: Incident, lang: str, extra: dict) -> str:
        names = self._names()
        subject = names.get(incident.subject) if incident.subject else None
        who = translate("who", lang, name=_name(subject)) if subject else ""
        hazard = translate(f"hazard_{incident.hazard}", lang)
        body = translate(key, lang, hazard=hazard, who=who, **extra)
        return f"{body}\n\n{translate('disclaimer', lang)}"

    def _buttons(self, incident: Incident, lang: str) -> list[list[dict]]:
        return [[{"text": translate("button_ack", lang), "callback_data": f"{CALLBACK}:{incident.token}:a"}],
                [{"text": translate("button_cancel", lang), "callback_data": f"{CALLBACK}:{incident.token}:c"}]]

    async def _alert(self, incident: Incident, slugs: list[str], tier: int, key: str, extra: dict) -> None:
        names = self._names()
        targets = [(chat_id, slug) for slug in slugs for chat_id in self.telegram.chats(slug)]
        if not targets:
            targets = [(chat_id, "") for chat_id in self.telegram.owners()]
        delivered = 0
        for chat_id, slug in targets:
            lang = (names.get(slug) or {}).get("ui_language") or None
            entry = {"chat": chat_id, "slug": slug, "tier": tier, "lang": lang,
                     "text": self._message(key, incident, lang, extra), "attempts": 0, "next": 0.0}
            if await self._send(incident, entry):
                delivered += 1
        self.audit("delivery", incident, {"delivered": delivered, "total": len(targets), "tier": tier})
        if delivered == 0:
            self.audit("unreachable", incident, {"hazard": incident.hazard})
            self.alarm.trigger(translate("unreachable"))

    async def _send(self, incident: Incident, entry: dict) -> bool:
        entry["attempts"] += 1
        message_id = await self.telegram.send(entry["chat"], entry["text"], self._buttons(incident, entry["lang"]))
        if message_id is not None:
            incident.recipients[entry["chat"]] = {"slug": entry["slug"], "tier": entry["tier"], "lang": entry["lang"],
                                                  "message": message_id}
            return True
        if entry["attempts"] < MAX_RETRIES:
            entry["next"] = self.clock() + RETRY_S[min(entry["attempts"] - 1, len(RETRY_S) - 1)]
            incident.retry.append(entry)
        return False

    async def _retry(self) -> None:
        incident = self.incident
        if incident is None or incident.closed or not incident.retry:
            return
        now = self.clock()
        due = [e for e in incident.retry if e["next"] <= now]
        incident.retry = [e for e in incident.retry if e["next"] > now]
        for entry in due:
            if entry["chat"] not in incident.recipients:
                await self._send(incident, entry)

    async def _notify_all(self, incident: Incident, key: str, values: dict, skip: str | None = None) -> None:
        for chat_id, info in list(incident.recipients.items()):
            await self.telegram.clear(chat_id, info["message"])
            if chat_id != skip:
                await self.telegram.send(chat_id, translate(key, info["lang"], **values), None)

    async def _acknowledged(self, tier: int) -> None:
        incident = self.incident
        if incident is None:
            return
        by = incident.recipients.get(incident.acked_by, {})
        name = _name(self._names().get(by.get("slug"))) or translate("someone")
        await self.ear({"type": "rescue_ack", "hazard": incident.hazard, "name": name})
        self.audit("acknowledged", incident, {"name": name, "tier": tier})
        await self._notify_all(incident, "acked_by", {"name": name}, skip=incident.acked_by or None)
        incident.retry.clear()

    async def _stand_down(self) -> None:
        self.alarm.stop()
        await self.ear({"type": "rescue_stop"})
        incident = self.incident
        if incident is None or incident.closed:
            return
        incident.closed = True
        incident.retry.clear()
        await self._notify_all(incident, "stand_down", {})

    async def callback(self, chat_id: str, data: str) -> str:
        parts = str(data or "").split(":")
        incident = self.incident
        if len(parts) != 3 or parts[0] != CALLBACK or parts[2] not in ("a", "c"):
            return translate("callback_stale")
        if incident is None or incident.closed or not secrets.compare_digest(parts[1], incident.token):
            return translate("callback_stale")
        info = incident.recipients.get(str(chat_id))
        if info is None:
            return translate("callback_stale")
        lang = info["lang"]
        now = self.clock()
        if parts[2] == "a":
            incident.acked_by = str(chat_id)
            self.coordinator.acknowledge(max(0, min(info["tier"], 99)), now=now)
        else:
            name = _name(self._names().get(info["slug"])) or translate("someone", lang)
            await self._notify_all(incident, "cancelled_by", {"name": name}, skip=str(chat_id))
            incident.closed = True
            incident.retry.clear()
            self.coordinator.dismiss(now=now)
        await self.flush()
        return translate("callback_ok", lang)


def _name(profile: dict | None) -> str:
    if not isinstance(profile, dict):
        return ""
    return html.escape(str(profile.get("nickname") or profile.get("first_name") or "")[:40], quote=False)
