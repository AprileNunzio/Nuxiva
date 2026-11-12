import logging
import time
from dataclasses import dataclass, field

from agenti._mastery import MasteryError, ledger as default_ledger

log = logging.getLogger("nuxiva.study")


@dataclass(frozen=True)
class Exercise:
    topic: str
    tier: int
    prompt: str
    data: dict = field(default_factory=dict)


def _pick(provider, agent: str, book) -> str | None:
    topics = [t for t in getattr(provider, "TOPICS", ()) if isinstance(t, str)]
    if not topics:
        return None
    ranked = []
    for topic in topics:
        state = book.standing(agent, topic)
        ranked.append((state["level"], state["attempts"], topic))
    return min(ranked)[2]


async def study(agent: str, provider, topic: str | None = None, book=None, now: int | None = None) -> dict | None:
    book = book or default_ledger
    chosen = topic or _pick(provider, agent, book)
    if chosen is None:
        return None
    before = book.standing(agent, chosen, now)
    exercise = provider.make(chosen, before["next"]["tier"])
    try:
        result = await provider.attempt(exercise)
        score, lesson = provider.grade(exercise, result)
    except (MasteryError, ValueError, TypeError, KeyError, RuntimeError, OSError) as exc:
        log.info("esercizio non riuscito (%s)", type(exc).__name__)
        score, lesson = 0.0, ""
    after = book.record(agent, chosen, exercise.tier, score, lesson, now if now is not None else int(time.time()))
    return {"agent": agent, "topic": chosen, "tier": exercise.tier, "kind": before["next"]["kind"], "score": score,
            "before": before["level"], "after": after["level"], "rank": after["rank"]}


async def session(agent: str, provider, rounds: int = 3, book=None) -> list[dict]:
    done = []
    for _ in range(max(0, min(rounds, 20))):
        out = await study(agent, provider, None, book)
        if out is None:
            break
        done.append(out)
    return done
