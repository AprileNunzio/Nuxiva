import asyncio
import json
import logging
import re
import time

import websockets

log = logging.getLogger("nuxiva.rescue.ear")
EAR_URL = "ws://127.0.0.1:8093/rescue"
MAX_MESSAGE = 2 ** 20
BACKOFF = (1.0, 2.0, 5.0, 10.0, 20.0)
SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
SOUND = {"scream": "scream", "smoke_alarm": "smoke", "co_alarm": "smoke"}
WORDS = (("help", "help_words"), ("threat", "violence"), ("fire", "fire"))
WORD_MIN = 0.5
ANSWER_MIN = 0.4
LOCKED = frozenset({"violence", "intrusion"})


def _unit(value) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value:
        return min(1.0, max(0.0, float(value)))
    return None


def translate(event: dict) -> list[tuple]:
    if not isinstance(event, dict) or event.get("type") != "danger":
        return []
    source = event.get("source")
    if source == "sound":
        kind = SOUND.get(event.get("kind"))
        p, c = _unit(event.get("probability")), _unit(event.get("confidence"))
        return [("observe", kind, p, c, "ear:sound")] if kind and p is not None and c is not None else []
    if source == "touch":
        answer = event.get("answer")
        return [("answer", answer, "touch")] if answer in ("ok", "not_ok") else []
    if source != "words":
        return []
    c = _unit(event.get("confidence"))
    if c is None:
        return []
    out: list[tuple] = []
    for field, kind in WORDS:
        p = _unit(event.get(field))
        if p is not None and p >= WORD_MIN:
            out.append(("observe", kind, p, c, "ear:words"))
    answer = event.get("answer")
    if not out and answer in ("ok", "not_ok") and event.get("asked") is True and c >= ANSWER_MIN:
        out.append(("answer", answer, "voice"))
    speaker = event.get("speaker")
    if isinstance(speaker, str) and SLUG.match(speaker):
        out.append(("subject", speaker))
    return out


class EarLink:
    def __init__(self, coordinator, dispatcher, clock=time.time) -> None:
        self.coordinator = coordinator
        self.dispatcher = dispatcher
        self.clock = clock
        self.ws = None
        self.connected = False

    def apply(self, event: dict) -> int:
        done = 0
        for item in translate(event):
            now = self.clock()
            if item[0] == "observe":
                _, kind, p, c, source = item
                try:
                    self.coordinator.observe(kind, p, c, source, at=now, now=now)
                    done += 1
                except ValueError as exc:
                    log.warning("Segnale d'ascolto di soccorso scartato: %s", exc)
            elif item[0] == "subject":
                self.dispatcher.note_subject(item[1], now)
            elif item[0] == "answer":
                done += self._answer(item[1], item[2], now)
        return done

    def _answer(self, answer: str, via: str, now: float) -> int:
        status = self.coordinator.status()
        if status.get("stage") not in ("check_in", "alerting", "acknowledged", "emergency"):
            return 0
        if answer == "not_ok":
            self.coordinator.need_help(now=now)
            return 1
        if status.get("hazard") in LOCKED:
            log.warning("Annullamento via %s ignorato per pericolo %s", via, status.get("hazard"))
            return 0
        self.coordinator.person_ok(now=now)
        return 1

    async def send(self, message: dict) -> bool:
        ws = self.ws
        if ws is None or not self.connected:
            return False
        try:
            await ws.send(json.dumps(message))
            return True
        except (websockets.ConnectionClosed, OSError, RuntimeError) as exc:
            log.debug("Ascolto non raggiungibile per il soccorso: %s", exc)
            return False

    async def session(self) -> None:
        async with websockets.connect(EAR_URL, max_size=MAX_MESSAGE, open_timeout=10) as ws:
            self.ws, self.connected = ws, True
            try:
                async for message in ws:
                    if not isinstance(message, str) or '"danger"' not in message:
                        continue
                    try:
                        event = json.loads(message)
                    except ValueError:
                        continue
                    if self.apply(event):
                        await self.dispatcher.flush()
            finally:
                self.ws, self.connected = None, False

    async def run(self, enabled) -> None:
        failures = 0
        while True:
            if not enabled():
                await asyncio.sleep(BACKOFF[-1])
                continue
            try:
                await self.session()
                failures = 0
            except (OSError, websockets.WebSocketException, asyncio.TimeoutError) as exc:
                log.debug("Collegamento all'ascolto per il soccorso: %s", exc)
                failures += 1
            await asyncio.sleep(BACKOFF[min(failures, len(BACKOFF) - 1)])
