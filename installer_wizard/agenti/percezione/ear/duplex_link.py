import json
import logging
import os
import time

import duplex

log = logging.getLogger("nuxiva.ear.duplex_link")
MODES = ("legacy", "rust")


def mode() -> str:
    value = os.environ.get("NUXIVA_DUPLEX", "legacy").strip().lower()
    return value if value in MODES else "legacy"


class DuplexLink:
    def __init__(self, clock=time.time):
        self._clock = clock
        self._session = None
        self.last_cut = None

    def active(self) -> bool:
        return mode() == "rust"

    def _now(self) -> int:
        return int(self._clock() * 1000)

    def _get(self):
        if self._session is None:
            self._session = duplex.build("", self._now())
        return self._session

    def snapshot(self) -> dict:
        return json.loads(self._get().snapshot()) if self.active() else {"state": "idle", "gen": 0}

    def _state(self, s) -> str:
        return json.loads(s.snapshot())["state"]

    def speaking(self, on: bool):
        if not self.active():
            return None
        s, now = self._get(), self._now()
        s.tick(now)
        before = self._state(s)
        try:
            if on:
                for step in {"idle": (), "listening": ("voice_end",), "thinking": (), "interrupted": ("resume", "voice_end"), "speaking": None}[before] or ():
                    s.trigger(step, now)
                if before != "speaking":
                    s.begin_reply(now)
            elif before == "speaking":
                s.finish(json.loads(s.snapshot())["gen"], now)
        except ValueError as exc:
            log.warning("transizione duplex rifiutata: %s", exc)
        after = self._state(s)
        return self.snapshot() if after != before else None

    def cut(self):
        if not self.active():
            return None
        s = self._get()
        try:
            report = json.loads(s.cut(0, self._now()))
        except ValueError as exc:
            log.warning("taglio duplex rifiutato: %s", exc)
            return None
        self.last_cut = report
        return report

    def tick(self):
        if not self.active():
            return None
        s, before = self._get(), self._state(self._get())
        s.tick(self._now())
        return self.snapshot() if self._state(s) != before else None

    async def handle(self, service, kind: str, msg: dict) -> bool:
        if kind == "speaking":
            changed = self.speaking(bool(msg.get("on")))
            if changed:
                await service.broadcast(type="duplex", **changed)
            return False
        if kind != "cut":
            return False
        service.nuxiva_speaking = False
        self.cut()
        await service.broadcast(type="barge", reason="manual")
        if self.active():
            await service.broadcast(type="duplex", **self.snapshot())
        return True


link = DuplexLink()
