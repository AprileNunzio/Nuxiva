import asyncio
import importlib
import logging
import os

from agenti import _study

log = logging.getLogger("nuxiva.study.runner")

MIN_HOURS = 1.0
MAX_ROUNDS = 5


def _hours() -> float:
    try:
        value = float(os.environ.get("NUXIVA_AGENT_STUDY_HOURS", "6"))
    except ValueError:
        return 6.0
    return 0.0 if value <= 0 else max(MIN_HOURS, min(value, 168.0))


def providers() -> list[tuple[str, object]]:
    from agenti._registry import registry
    found = []
    for agent in registry.agents():
        if not (agent.dir / "exercises.py").is_file():
            continue
        try:
            module = importlib.import_module(f"{agent.module}.exercises")
        except (ImportError, SyntaxError) as exc:
            log.warning("esercizi di %s non caricabili (%s)", agent.id, type(exc).__name__)
            continue
        if all(hasattr(module, name) for name in ("TOPICS", "make", "attempt", "grade")):
            found.append((agent.id, module))
    return found


async def round_all(rounds: int = 2) -> list[dict]:
    done = []
    for ident, module in providers():
        try:
            done.extend(await _study.session(ident, module, min(rounds, MAX_ROUNDS)))
        except (ValueError, OSError, RuntimeError) as exc:
            log.warning("studio di %s interrotto (%s)", ident, type(exc).__name__)
    return done


async def run() -> None:
    hours = _hours()
    if hours == 0.0:
        return
    await asyncio.sleep(600)
    while True:
        done = await round_all()
        log.info("studio degli agenti: %d esercizi", len(done))
        await asyncio.sleep(hours * 3600)
