from dataclasses import dataclass
from typing import List, Sequence

from .models import Message

HISTORY_TURNS = 12
HISTORY_CHARS = 12000
TURN_CHARS = 2400


class StudioBrainUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ModeProfile:
    kind: str
    max_tokens: int
    temperature: float
    timeout: float


PROFILES = {
    "fast": ModeProfile("chat", 900, 0.3, 60.0),
    "reasoning": ModeProfile("deep", 4000, 0.2, 180.0),
    "creative": ModeProfile("chat", 2400, 0.9, 120.0),
    "code": ModeProfile("deep", 6000, 0.1, 240.0),
}


def profile_for(mode: str) -> ModeProfile:
    return PROFILES.get(mode, PROFILES["reasoning"])


def transcript(history: Sequence[Message]) -> str:
    lines: List[str] = []
    budget = HISTORY_CHARS
    for message in reversed([m for m in history if m.role in ("user", "assistant") and m.content.strip()][-HISTORY_TURNS:]):
        who = "Utente" if message.role == "user" else "Nuxiva"
        line = f"{who}: {message.content.strip()[:TURN_CHARS]}"
        if len(line) > budget:
            break
        budget -= len(line)
        lines.append(line)
    return "\n\n".join(reversed(lines))


def build_prompt(content: str, history: Sequence[Message], attachment_summary: str = "") -> str:
    parts = []
    previous = transcript(history)
    if previous:
        parts.append(f"[Conversazione precedente]\n{previous}")
    if attachment_summary:
        parts.append(attachment_summary.strip())
    parts.append(f"Richiesta utente: {content}")
    return "\n\n".join(parts)


async def infer(prompt: str, system: str, mode: str) -> str:
    from agenti.brain.llm import BrainUnavailable, generate
    profile = profile_for(mode)
    try:
        reply = await generate(prompt, system=system, kind=profile.kind, max_tokens=profile.max_tokens,
                               temperature=profile.temperature, timeout=profile.timeout)
    except BrainUnavailable as exc:
        raise StudioBrainUnavailable(str(exc)[:300]) from exc
    text = reply if isinstance(reply, str) else str(reply or "")
    if not text.strip():
        raise StudioBrainUnavailable("risposta vuota dal modello")
    return text
