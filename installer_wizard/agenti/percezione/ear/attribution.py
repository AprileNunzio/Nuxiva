import time

import numpy as np

import native_core

import earconf

MAX_FOREIGN = 8
FOREIGN_JOIN = 0.6
FOREIGN_BLEND = 0.2
FOREIGN_BLOCK = 0.7
FOREIGN_FORGET_S = 1800.0
FOREIGN_RECURRING = 3
SESSION_S = 20.0
SESSION_FLOOR = 0.5
SESSION_BLEND = 0.25
SCORE_CAP = 0.97
RECENT_S = 120.0


def policy() -> tuple:
    return (earconf.number("NUXIVA_VOICE_MIN_SECONDS", 1.2, 0.5, 10.0),
            earconf.number("NUXIVA_VOICE_STRICT_BONUS", 0.05, 0.0, 0.3),
            earconf.number("NUXIVA_VOICE_PROGRAMME_BONUS", 0.08, 0.0, 0.3),
            earconf.number("NUXIVA_VOICE_FOREIGN_MARGIN", 0.1, 0.0, 0.5),
            earconf.number("NUXIVA_VOICE_WINDOW_GAP", 0.04, 0.0, 0.3),
            earconf.number("NUXIVA_VOICE_CLEAR_GAP", 0.08, 0.0, 0.4))


def _unit(v) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32)
    return v / max(float(np.linalg.norm(v)), 1e-9)


def _verdict(slug, verified, foreign, score, needed, reason) -> dict:
    return {"slug": slug, "verified": verified, "foreign": foreign, "score": score, "needed": needed, "reason": reason}


class PyAttributor:

    def __init__(self, *args) -> None:
        (self.min_seconds, self.strict_bonus, self.programme_bonus, self.foreign_margin,
         self.window_gap, self.clear_gap) = args or policy()
        self.foreign: list[dict] = []
        self.sessions: dict[str, dict] = {}

    def clear(self) -> None:
        self.foreign, self.sessions = [], {}

    def foreign_count(self) -> int:
        return len(self.foreign)

    def foreign_recent(self, now: float, within: float) -> int:
        return sum(1 for f in self.foreign if f["turns"] >= FOREIGN_RECURRING and now - f["seen"] <= within)

    def _note(self, probe, now) -> None:
        best = None
        for i, f in enumerate(self.foreign):
            sim = float(f["centre"] @ probe)
            if sim >= FOREIGN_JOIN and (best is None or sim > best[1]):
                best = (i, sim)
        if best is not None:
            f = self.foreign[best[0]]
            f["centre"] = _unit((1 - FOREIGN_BLEND) * f["centre"] + FOREIGN_BLEND * probe)
            f["seen"], f["turns"] = now, f["turns"] + 1
            return
        self.foreign.append({"centre": probe, "seen": now, "turns": 1})
        if len(self.foreign) > MAX_FOREIGN:
            self.foreign = sorted(self.foreign, key=lambda f: f["seen"], reverse=True)[:MAX_FOREIGN]

    def judge(self, probe, slug, score, limit, seconds, programme, windows, now) -> dict:
        values = [score, limit, seconds, now]
        arr = np.asarray(probe, dtype=np.float32)
        if arr.size == 0 or arr.size > 1024 or not np.all(np.isfinite(arr)) or not all(np.isfinite(values)) or len(windows) > 16:
            return _verdict(None, False, False, 0.0, 0.0, "dati non validi")
        self.foreign = [f for f in self.foreign if now - f["seen"] <= FOREIGN_FORGET_S]
        self.sessions = {k: v for k, v in self.sessions.items() if now - v["seen"] <= SESSION_S}
        probe = _unit(arr)
        if seconds < self.min_seconds:
            return _verdict(None, False, False, score, 0.0, "troppo breve")
        if slug is None:
            if score < limit - self.clear_gap or score <= 0.0:
                self._note(probe, now)
            return _verdict(None, False, False, score, limit, "voce non registrata")
        needed = min(limit + self.strict_bonus + (self.programme_bonus if programme else 0.0), SCORE_CAP)
        if score < needed:
            return _verdict(None, False, False, score, needed, "prova insufficiente")
        floor = limit - self.window_gap
        if not all(w[0] == slug and w[1] >= floor for w in windows):
            return _verdict(None, False, False, score, needed, "voci miste o incerte")
        other = max((float(f["centre"] @ probe) for f in self.foreign if f["turns"] >= 2), default=0.0)
        if other >= FOREIGN_BLOCK and other + self.foreign_margin > score:
            return _verdict(None, False, True, score, needed, "somiglia a una voce estranea")
        session = self.sessions.get(slug)
        if session is not None and float(session["centre"] @ probe) < SESSION_FLOOR:
            del self.sessions[slug]
            return _verdict(None, False, False, score, needed, "cambio di voce nella sessione")
        if session is not None:
            centre = _unit((1 - SESSION_BLEND) * session["centre"] + SESSION_BLEND * probe)
        else:
            centre = probe
        if session is not None or len(self.sessions) < 16:
            self.sessions[slug] = {"centre": centre, "seen": now}
        return _verdict(slug, True, False, score, needed, "ok")


def build():
    engine = native_core.symbol("RustAttributor")
    if engine is None:
        native_core.python_fallback("ear.attribution")
        return PyAttributor()
    return engine(*policy())


class Attribution:

    def __init__(self) -> None:
        self.engine = build()

    def judge(self, probe, slug, score, limit, seconds, programme, windows, now=None) -> dict:
        when = time.time() if now is None else now
        return self.engine.judge(np.asarray(probe, dtype=np.float32).tolist(), slug, float(score), float(limit),
                                 float(seconds), bool(programme), [(w[0], float(w[1])) for w in windows], float(when))

    def recent(self, now=None) -> int:
        return self.engine.foreign_recent(time.time() if now is None else now, RECENT_S)

    def clear(self) -> None:
        self.engine.clear()
