import asyncio
import json
import time

from state import store

from agenti.reasoning import models, pipeline, state, traces
from agenti.reasoning.contracts import CHAT
from agenti.reasoning.invoker import Invoker

DONE = ("done", "replayed")


def active() -> bool:
    if not state.ready() or state.emergency_off():
        return False
    try:
        return json.loads(state.engine().status(state.now_ms()))["switch"]["mode"] == "active"
    except state.Unavailable:
        return False


def _reply(report: dict, invoker: Invoker, lang: str) -> str:
    done = [s for s in report["steps"] if s["status"] in DONE and s.get("output")]
    text = done[-1]["output"] if done else ""
    if not report["complete"]:
        text = f"{text}\n{traces.message('partial', lang)}".strip()
    return text


async def attempt(text: str, role: str, lang: str) -> dict | None:
    started = time.time()
    try:
        thought = await pipeline.think(text, role)
    except (models.ModelFailed, state.Unavailable) as exc:
        store.event("WARN", f"Motore attivo non disponibile, uso il percorso precedente: {exc}", "reasoning")
        return None
    if not thought.executable or CHAT in thought.capabilities:
        traces.add("fallback", thought.public())
        return None
    invoker = Invoker(text, asyncio.get_running_loop())
    try:
        report = json.loads(await asyncio.to_thread(state.engine().execute, thought.raw_goal, text, role,
                                                    json.dumps(thought.checked["plan"]), state.journal_dir(), state.key(), invoker))
    except (ValueError, OSError) as exc:
        store.event("ERROR", f"Esecuzione del piano non riuscita, uso il percorso precedente: {exc}", "reasoning")
        traces.add("error", thought.public(), error=str(exc)[:200])
        return None
    executed = any(s["status"] in DONE for s in report["steps"])
    traces.add("active", thought.public(), complete=report["complete"], executed=executed, errors=invoker.errors[:4])
    if not executed:
        return None
    return {"reply": _reply(report, invoker, lang), "ui": invoker.ui, "intent": "reasoning", "agent": f"reasoning · {invoker.agent or 'plan'}",
            "elapsed_ms": int((time.time() - started) * 1000), "plan": thought.public()}
