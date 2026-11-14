import asyncio
import json
import logging
import re

from agenti.brain.llm import BrainUnavailable, generate

log = logging.getLogger("nuxiva.brain")
MAX_STEPS = 6
MAX_PROMPT_BYTES = 64 * 1024
TIMEOUT = 45.0
SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")
STEP_KEYS = {"id", "worker_template", "intent", "goal_ref", "needs_graph", "budget", "verify"}
BUDGET_KEYS = {"tokens", "tool_calls", "time_ms"}
VERIFY = {"none", "judge", "evidence"}
SYSTEM = (
    "Sei il pianificatore di un sistema multi-agente. Rispondi solo con un oggetto JSON valido con le chiavi "
    "schema_version, id, steps, edges. Ogni passo ha id, worker_template, intent, goal_ref, needs_graph, "
    "budget{tokens,tool_calls,time_ms}, verify (none|judge|evidence). Usa solo gli agenti e gli intenti offerti. "
    f"Al massimo {MAX_STEPS} passi. Ogni arco ha from e to e non deve creare cicli."
)


class PlanRejected(ValueError):
    pass


def parse_prompt(raw: str) -> dict:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_PROMPT_BYTES:
        raise PlanRejected("prompt")
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get("task"), dict) or not isinstance(data.get("offers"), list):
        raise PlanRejected("prompt")
    return data


def offers_index(prompt: dict) -> dict:
    index = {}
    for offer in prompt["offers"]:
        if isinstance(offer, dict) and isinstance(offer.get("worker_template"), str):
            index[offer["worker_template"]] = offer
    return index


def validate(plan, prompt: dict) -> dict:
    if not isinstance(plan, dict) or set(plan) - {"schema_version", "id", "steps", "edges"}:
        raise PlanRejected("shape")
    steps = plan.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        raise PlanRejected("steps")
    offers = offers_index(prompt)
    seen = set()
    for step in steps:
        if not isinstance(step, dict) or set(step) != STEP_KEYS:
            raise PlanRejected("step")
        if not all(isinstance(step[k], str) and SLUG.match(step[k]) for k in ("id", "worker_template", "intent", "goal_ref")):
            raise PlanRejected("ident")
        offer = offers.get(step["worker_template"])
        if offer is None or step["intent"] not in offer.get("intents", []) or step["id"] in seen:
            raise PlanRejected("offer")
        seen.add(step["id"])
        budget = step["budget"]
        if not isinstance(budget, dict) or set(budget) != BUDGET_KEYS or not all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in budget.values()):
            raise PlanRejected("budget")
        if budget["tokens"] > offer.get("tokens_max", 0) or budget["tool_calls"] > offer.get("tool_calls_max", 0) or budget["time_ms"] > offer.get("time_ms", 0):
            raise PlanRejected("budget")
        if not isinstance(step["needs_graph"], bool) or step["verify"] not in VERIFY:
            raise PlanRejected("step")
    edges = plan.get("edges", [])
    if not isinstance(edges, list) or len(edges) > MAX_STEPS * MAX_STEPS:
        raise PlanRejected("edges")
    for edge in edges:
        if not isinstance(edge, dict) or set(edge) != {"from", "to"} or edge["from"] not in seen or edge["to"] not in seen:
            raise PlanRejected("edge")
    return {"schema_version": plan.get("schema_version", 1), "id": plan.get("id"), "steps": steps, "edges": edges}


def build_prompt(prompt: dict) -> str:
    body = {"task": prompt["task"], "offers": prompt["offers"], "attempt": prompt.get("attempt"), "rejected": prompt.get("rejected")}
    return json.dumps(body, ensure_ascii=False)


def make(loop: asyncio.AbstractEventLoop, person: str = ""):
    def planner(raw: str) -> str:
        prompt = parse_prompt(raw)
        future = asyncio.run_coroutine_threadsafe(
            generate(build_prompt(prompt), as_json=True, kind="deep", system=SYSTEM, max_tokens=900, temperature=0.0,
                     timeout=TIMEOUT, person=person), loop)
        try:
            produced = future.result(TIMEOUT + 5)
        except BrainUnavailable as error:
            raise PlanRejected("brain") from error
        except TimeoutError as error:
            future.cancel()
            raise PlanRejected("timeout") from error
        if isinstance(produced, str):
            produced = json.loads(produced)
        return json.dumps(validate(produced, prompt))
    return planner
