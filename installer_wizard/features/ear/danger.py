import time

import numpy as np

import earconf
import native_core
from distress import analyze

ASK_MAX = 120.0
NOTABLE = 0.2
PROMPTS = {"rescue_ask": "ask", "rescue_remind": "remind", "rescue_ack": "ack", "rescue_stop": "stop"}
CONTROLS = frozenset({*PROMPTS, "rescue_answer"})
HAZARDS = frozenset({"medical", "fire", "intrusion", "violence"})
ANSWERS = frozenset({"ok", "not_ok"})
NAME_MAX = 40


class DangerEar:
    def __init__(self) -> None:
        engine = native_core.symbol("RustDangerSound")
        if engine is None:
            native_core.python_fallback("ear.danger_sound")
        self.engine = engine() if engine is not None else None
        self.asked_until = 0.0

    @staticmethod
    def enabled() -> bool:
        return earconf.flag("NUXIVA_RESCUE_LISTEN", True)

    def ask(self, seconds) -> None:
        value = float(seconds) if isinstance(seconds, (int, float)) and not isinstance(seconds, bool) else 30.0
        value = value if value == value else 30.0
        self.asked_until = time.time() + max(5.0, min(ASK_MAX, value))

    def asked(self) -> bool:
        return time.time() < self.asked_until

    def frame(self, frame: np.ndarray, media: bool, speaking: bool) -> list[dict]:
        if self.engine is None or not self.enabled():
            return []
        events = self.engine.feed(np.ascontiguousarray(frame, dtype="<f4").tobytes(), bool(media))
        return [{"kind": kind, "probability": round(p, 4), "confidence": round(c, 4), "duration": round(d, 3)}
                for kind, p, c, _, d in events if not (speaking and kind == "scream")]

    def text(self, text: str, media: bool, speech_confidence: float = 0.8) -> dict | None:
        if not self.enabled() or not text or not text.strip():
            return None
        asked = self.asked()
        verdict = analyze(text, asked, media, speech_confidence)
        notable = max(verdict["help"], verdict["threat"], verdict["fire"]) >= NOTABLE
        if not notable and not (asked and verdict["answer"]):
            return None
        if asked and verdict["answer"]:
            self.asked_until = 0.0
        return {"help": round(verdict["help"], 4), "threat": round(verdict["threat"], 4),
                "fire": round(verdict["fire"], 4), "confidence": round(verdict["confidence"], 4),
                "answer": verdict["answer"], "asked": asked, "lang": verdict["lang"],
                "cues": [d["cue"] for d in verdict["detections"] if not d["negated"]][:8]}


def _name(value) -> str:
    text = value if isinstance(value, str) else ""
    return "".join(c for c in text if c.isalpha() or c in " '-.")[:NAME_MAX].strip()


async def rescue_control(kind: str, msg: dict, sessions, broadcast) -> None:
    if kind == "rescue_answer":
        answer = msg.get("answer")
        if answer in ANSWERS:
            await broadcast(type="danger", source="touch", answer=answer)
        return
    stage = PROMPTS.get(kind)
    if stage is None:
        return
    seconds = msg.get("seconds")
    if stage == "ask":
        for session in list(sessions):
            session.danger.ask(seconds)
    elif stage == "stop":
        for session in list(sessions):
            session.danger.asked_until = 0.0
    hazard = msg.get("hazard") if msg.get("hazard") in HAZARDS else "medical"
    tone = "discreet" if msg.get("tone") == "discreet" else "spoken"
    wait = int(max(5.0, min(ASK_MAX, seconds))) if isinstance(seconds, (int, float)) and not isinstance(seconds, bool) and seconds == seconds else 30
    raw = msg.get("number")
    number = raw if isinstance(raw, str) and 2 <= len(raw) <= 6 and all(c in "0123456789" for c in raw) else "112"
    await broadcast(type="rescue_prompt", stage=stage, hazard=hazard, tone=tone, seconds=wait, number=number,
                    name=_name(msg.get("name")))
