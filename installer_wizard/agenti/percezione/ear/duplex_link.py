import json
import logging
import os
import time

import barge
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
        self._barge = None
        self.counts = {"replies": 0, "cuts": 0, "manual_cuts": 0, "timeouts": 0, "voice_cuts": 0}

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
                    self.counts["replies"] += 1
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
        self.counts["cuts"] += 1
        return report

    def barge_step(self, verdict: str, margin: int, voiced: bool):
        if not self.active():
            return None
        if self._barge is None:
            self._barge = barge.build("", True)
        s = self._get()
        out = json.loads(self._barge.step(s, verdict, margin, voiced, 250, self._now()))
        if out["decision"] == "cut":
            self.last_cut = out["report"]
            self.counts["cuts"] += 1
            self.counts["voice_cuts"] += 1
        return out["decision"]

    def tick(self):
        if not self.active():
            return None
        s, before = self._get(), self._state(self._get())
        s.tick(self._now())
        changed = self._state(s) != before
        self.counts["timeouts"] += int(changed)
        return self.snapshot() if changed else None

    def health(self) -> dict:
        snap = self.snapshot()
        return {"mode": mode(), "state": snap["state"], "generation": snap["gen"], "bound_tokens": snap.get("bound_tokens", 0), **self.counts}

    async def handle(self, service, kind: str, msg: dict) -> bool:
        if kind == "speaking":
            changed = self.speaking(bool(msg.get("on")))
            if changed:
                await service.broadcast(type="duplex", **changed)
            return False
        if kind != "cut":
            return False
        service.nuxiva_speaking = False
        self.counts["manual_cuts"] += 1
        self.cut()
        await service.broadcast(type="barge", reason="manual")
        if self.active():
            await service.broadcast(type="duplex", **self.snapshot())
        return True


link = DuplexLink()
