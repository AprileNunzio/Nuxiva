import hashlib
import json
import logging
import re
import secrets

from config import STATE_DIR
from state import store

from agenti.agency.client import AgencyRejected, AgencyUnavailable, client
from agenti.agency.foresight import prompts, scenario
from agenti.agency.memory import ProjectMemory
from agenti.agency.text import clean, unique_id
from agenti.agency.words import dictionary, lang_of
from agenti.brain import llm
from agenti.brain.llm import BrainUnavailable

log = logging.getLogger("nuxiva.agency.foresight")
memory = ProjectMemory(STATE_DIR / "agency" / "foresight")
AGENT_KEY = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
MATERIAL_MIN, MATERIAL_MAX = 20, 60_000
QUESTION_MIN, QUESTION_MAX = 8, 2_000
MESSAGE_MAX = 1_000
POPULATION = (2, 2_000, 200)
ROUNDS = (4, 720, 48)
RUNS = (1, 64, 16)
WORLD_TOKENS, REPORT_TOKENS, VOICE_TOKENS = 4_000, 2_200, 500
HISTORY = 12
MAX_CHUNKS = 800


class ForesightFailure(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _bounded(value, limits: tuple[int, int, int]) -> int:
    low, high, default = limits
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return min(high, max(low, number))


def _question(raw) -> str:
    text = "\n".join(" ".join(line.split()) for line in clean(raw, QUESTION_MAX).splitlines()).strip()
    if len(text) < QUESTION_MIN:
        raise ForesightFailure("question")
    return text


def _context(simulation_id: str) -> dict:
    try:
        return memory.load(simulation_id)
    except (KeyError, FileNotFoundError, ValueError):
        return {}


async def create(material: str, question: str, lang: str, population=None, rounds=None) -> dict:
    lang = lang_of(lang)
    material = clean(material, MATERIAL_MAX)
    if len(material) < MATERIAL_MIN:
        raise ForesightFailure("material")
    question = _question(question)
    population = _bounded(population, POPULATION)
    rounds = _bounded(rounds, ROUNDS)
    language_name = dictionary(lang)["language_name"]
    try:
        raw = await llm.generate(prompts.world(material, question, rounds, language_name), as_json=True,
                                 max_tokens=WORLD_TOKENS, temperature=0.3, system=prompts.ARCHITECT,
                                 component="agency_foresight")
    except BrainUnavailable as exc:
        raise ForesightFailure("brain") from exc
    seed = secrets.randbits(63)
    spec, personas = scenario.build(raw, question, population, rounds, seed)
    if not spec:
        raise ForesightFailure("empty_world")
    simulation_id = unique_id(spec["title"])
    summary = await client.call("foresight_create", id=simulation_id, scenario=spec)
    memory.save(simulation_id, {"lang": lang, "personas": personas, "entities": spec["entities"],
                                "narrative": None, "chats": {}})
    store.event("INFO", f"Foresight {simulation_id} created with {len(spec['agents'])} agents", "agency")
    return summary


async def simulate(simulation_id: str) -> dict:
    result = {}
    for _ in range(MAX_CHUNKS):
        result = await client.call("foresight_run", id=simulation_id)
        if result.get("finished") or not result.get("advanced"):
            break
    return result


async def launch(material: str, question: str, lang: str, population=None, rounds=None) -> None:
    try:
        summary = await create(material, question, lang, population, rounds)
        await simulate(summary["id"])
    except ForesightFailure as exc:
        store.event("WARN", f"Foresight not started: {exc.code}", "agency")
    except (AgencyRejected, AgencyUnavailable, OSError) as exc:
        log.error("Foresight launch failed: %s", type(exc).__name__)
        store.event("ERROR", f"Foresight launch failed: {type(exc).__name__}", "agency")


async def resume(simulation_id: str) -> None:
    try:
        await simulate(simulation_id)
    except (AgencyRejected, AgencyUnavailable) as exc:
        store.event("WARN", f"Foresight {simulation_id} stopped: {type(exc).__name__}", "agency")


async def overview() -> list:
    return await client.call("foresight_list")


async def inject(simulation_id: str, raw: dict) -> dict:
    context = _context(simulation_id)
    report = await client.call("foresight_report", id=simulation_id)
    current = int(report["report"]["round"])
    rounds = int(report["report"]["rounds"])
    event = scenario.event_spec(raw, rounds, scenario.aliases_of(context.get("entities", [])), current + 1)
    if event is None:
        raise ForesightFailure("event")
    return await client.call("foresight_inject", id=simulation_id, event=event)


async def ensemble(simulation_id: str, runs) -> dict:
    return await client.call("foresight_ensemble", id=simulation_id, runs=_bounded(runs, RUNS))


def _signature(data: dict) -> str:
    report = data.get("report", {})
    ensemble_data = data.get("ensemble") or {}
    basis = [report.get("round"), len(report.get("events", [])), ensemble_data.get("runs")]
    return hashlib.sha256(json.dumps(basis).encode()).hexdigest()[:16]


async def detail(simulation_id: str) -> dict:
    data = await client.call("foresight_report", id=simulation_id)
    narrative = _context(simulation_id).get("narrative") or {}
    fresh = narrative.get("signature") == _signature(data)
    return {**data, "narrative": narrative.get("text") if fresh else None, "narrative_stale": not fresh}


def _digest(data: dict) -> dict:
    report = data["report"]
    step = max(1, len(report["trajectory"]) // 24)
    return {"question": report["question"], "rounds": report["round"], "agents": report["agents"],
            "outcome": report["outcome"], "trajectory": report["trajectory"][::step],
            "roles": report["roles"], "entities": report["entities"], "events": report["events"],
            "influencers": report["influencers"][:6], "movers": report["movers"][:6],
            "notable": report["notable"][:6], "ensemble": data.get("ensemble")}


async def narrate(simulation_id: str, lang: str) -> dict:
    data = await client.call("foresight_report", id=simulation_id)
    context = _context(simulation_id)
    language_name = dictionary(lang_of(lang or context.get("lang", "it")))["language_name"]
    try:
        text = await llm.generate(prompts.report(_digest(data), language_name), max_tokens=REPORT_TOKENS,
                                  temperature=0.3, system=prompts.REPORTER, component="agency_foresight_report")
    except BrainUnavailable as exc:
        raise ForesightFailure("brain") from exc
    text = clean(text, 40_000)
    if context:
        memory.update(simulation_id, narrative={"signature": _signature(data), "text": text})
    return {**data, "narrative": text, "narrative_stale": False}


async def agent(simulation_id: str, agent_key: str) -> dict:
    if not AGENT_KEY.fullmatch(agent_key):
        raise ForesightFailure("not_found")
    view = await client.call("foresight_agent", id=simulation_id, agent=agent_key)
    context = _context(simulation_id)
    view["persona"] = context.get("personas", {}).get(agent_key, "")
    view["chat"] = context.get("chats", {}).get(agent_key, [])
    return view


async def chat(simulation_id: str, agent_key: str, message: str, lang: str) -> dict:
    message = " ".join(clean(message, MESSAGE_MAX).split())
    if not message:
        raise ForesightFailure("message")
    view = await agent(simulation_id, agent_key)
    history = view.pop("chat")[-HISTORY:]
    language_name = dictionary(lang_of(lang))["language_name"]
    try:
        answer = await llm.generate(prompts.voice(view, history, message, language_name), max_tokens=VOICE_TOKENS,
                                    temperature=0.6, system=prompts.VOICE, component="agency_foresight")
    except BrainUnavailable as exc:
        raise ForesightFailure("brain") from exc
    answer = clean(answer, 4_000)
    history = (history + [{"who": "user", "text": message}, {"who": view["name"], "text": answer}])[-HISTORY:]
    context = _context(simulation_id)
    if context:
        chats = context.get("chats", {})
        chats[agent_key] = history
        memory.update(simulation_id, chats=chats)
    return {"answer": answer, "chat": history}


async def delete(simulation_id: str) -> dict:
    result = await client.call("foresight_delete", id=simulation_id)
    memory.forget(simulation_id)
    return result
