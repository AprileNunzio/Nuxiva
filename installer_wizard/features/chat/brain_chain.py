import asyncio
import time
from dataclasses import replace
from itertools import groupby
from typing import Any, Awaitable, Callable, Dict, List, Optional

from state import store
from tasks import background

from features.brain import stages
from features.brain.brains import brains
from features.brain.components import LimbicModulator, SpikingNeuron
from features.brain.residency import touch
from features.brain.trace import trace
from features.cloud import conversation
from features.cloud.catalog import is_cloud
from features.cloud.client import CloudError
from features.twin.simulator import predict_user_impact
from server.core.reasoning.engines.auto_6_5.engine import COMPLEXITY_WORDS
from server.core.reasoning.engines.base import CONFIDENCE_WEIGHT, CRITIC_WEIGHT, Strategy

CONFIDENCE_OK = 0.88
CONFIDENCE_BAD = 0.35
HARD_TIMEOUT_S = 240.0
DEFAULT_MODE = "nuxiva-6.5-auto"
LEGACY_IDS = {"nuxiva-5.0-fast": "nuxiva-5.0-veloce", "nuxiva-5.0-empathetic": "nuxiva-5.0-empatico", "empathetic": "empatico"}

Generator = Callable[[str, Dict[str, Any], LimbicModulator], Awaitable[Dict[str, Any]]]


class NoBrainAvailable(RuntimeError):
    pass


def _scanner():
    from server.core.reasoning.engines.scanner import engine_scanner
    return engine_scanner


def valid(candidate: Dict[str, Any]) -> bool:
    text = str(candidate.get("text") or "").strip()
    return bool(text) and not text.lower().startswith("errore")


class CorticalBrainChain:
    def __init__(self) -> None:
        self.limbic = LimbicModulator()
        self.neurons: Dict[str, SpikingNeuron] = {}
        self.active_mode: str = DEFAULT_MODE

    def set_mode(self, mode_id: str) -> str:
        wanted = str(mode_id or "").strip().lower()
        wanted = LEGACY_IDS.get(wanted, wanted)
        scanner = _scanner()
        engine = scanner.get_engine(wanted) if wanted else None
        engine = engine or scanner.get_default_engine()
        self.active_mode = getattr(engine.version, "value", str(engine.version)) if engine else DEFAULT_MODE
        return self.active_mode

    def engine(self):
        scanner = _scanner()
        return scanner.get_engine(self.active_mode) or scanner.get_default_engine()

    def strategy_for(self, query: str) -> Strategy:
        return self.engine().effective(query, self.limbic).strategy

    def register_cortical_column(self, neuron: SpikingNeuron) -> None:
        self.neurons[neuron.neuron_id] = neuron

    async def _score(self, candidate: Dict[str, Any], plan: Strategy, critic_fn) -> float:
        confidence = float(candidate.get("confidence", CONFIDENCE_BAD))
        if not plan.critic or critic_fn is None:
            return confidence
        critic = await critic_fn(candidate, self.limbic)
        candidate["critic"] = round(float(critic), 3)
        return confidence * CONFIDENCE_WEIGHT + float(critic) * CRITIC_WEIGHT

    async def _sequential(self, query: str, context: Dict[str, Any], generators: List[Generator],
                          errors: List[str]) -> List[Dict[str, Any]]:
        for idx, gen in enumerate(generators):
            try:
                candidate = await asyncio.wait_for(gen(query, context, self.limbic), HARD_TIMEOUT_S)
            except Exception as exc:
                errors.append(f"{idx}: {type(exc).__name__}: {str(exc)[:120]}")
                continue
            candidate["branch_id"] = idx
            if valid(candidate):
                return [candidate]
        return []

    async def _parallel(self, query: str, context: Dict[str, Any], generators: List[Generator], plan: Strategy,
                        errors: List[str]) -> List[Dict[str, Any]]:
        tasks = {asyncio.create_task(gen(query, dict(context), self.limbic)): idx for idx, gen in enumerate(generators)}
        answers: List[Dict[str, Any]] = []
        loop = asyncio.get_running_loop()
        hard_end = loop.time() + HARD_TIMEOUT_S
        soft_end: Optional[float] = None
        pending = set(tasks)
        try:
            while pending:
                end = min(hard_end, soft_end) if soft_end is not None else hard_end
                remaining = end - loop.time()
                if remaining <= 0:
                    break
                done, pending = await asyncio.wait(pending, timeout=remaining, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    exc = task.exception()
                    if exc is not None:
                        errors.append(f"{tasks[task]}: {type(exc).__name__}: {str(exc)[:120]}")
                        continue
                    candidate = task.result()
                    candidate["branch_id"] = tasks[task]
                    if valid(candidate):
                        answers.append(candidate)
                if answers and plan.pick == "first":
                    break
                if answers and soft_end is None:
                    soft_end = loop.time() + plan.wait_s
        finally:
            for task in pending:
                task.cancel()
        return answers

    async def execute_parallel_thought(self, query: str, context: Dict[str, Any], branch_generators: List[Generator],
                                       critic_fn: Optional[Callable[[Dict[str, Any], LimbicModulator], Awaitable[float]]] = None,
                                       plan: Optional[Strategy] = None) -> Dict[str, Any]:
        started = time.perf_counter()
        plan = plan or self.strategy_for(query)
        launched = branch_generators[:plan.candidates]
        reserve = branch_generators[plan.candidates:]
        errors: List[str] = []
        if plan.pick == "sequential":
            answers = await self._sequential(query, context, branch_generators, errors)
        else:
            answers = await self._parallel(query, context, launched, plan, errors) if launched else []
            if not answers and reserve:
                answers = await self._sequential(query, context, reserve, errors)
        best: Dict[str, Any] = {"text": "", "score": 0.0}
        for candidate in answers:
            candidate["score"] = round(await self._score(candidate, plan, critic_fn), 3)
            if candidate["score"] > best.get("score", 0.0) or not best.get("text"):
                best = candidate
        best.update({
            "mode": self.active_mode,
            "strategy": plan.as_dict(),
            "candidates_launched": len(branch_generators) if plan.pick == "sequential" else len(launched),
            "candidates_answered": len(answers),
            "errors": errors,
            "latency_ms": round((time.perf_counter() - started) * 1000.0, 2),
            "limbic_snapshot": {k: round(float(getattr(self.limbic, k)), 3)
                                for k in ("valence", "arousal", "dopamine", "noradrenaline", "serotonin", "cortisol")},
        })
        return best


cortical_chain = CorticalBrainChain()


def engine_label(lang: Any = None) -> str:
    engine = _scanner().get_engine(DEFAULT_MODE) or _scanner().get_default_engine()
    return engine.label(lang)


async def _cloud(ref: str, query: str, device: str, context: dict, route: dict) -> dict:
    started = time.time()
    call = trace.begin("conversation", route["reason"], route["models"])
    trace.attempt(call, ref)
    label = engine_label(route.get("lang"))
    try:
        answer = await conversation.reply(ref, query, device, context, route["max_tokens"], remember_turn=route.get("remember", True))
    except CloudError as exc:
        brains.record(ref, (time.time() - started) * 1000, False, route["kind"])
        trace.abort(call, str(exc))
        raise
    brains.record(ref, answer.ms, True, route["kind"])
    if route.get("free_matrix_active"):
        from features.brain.free_router.failover_engine import pool_for, succeeded
        succeeded(ref, ref.removeprefix("cloud:openrouter/"), answer.ms, pool_for(ref, route.get("task_pool", "chat")))
    trace.finish(call, ref, answer.ms, answer.text)
    background(touch(ref))
    return {
        "agent_id": f"nuxiva_cloud · {ref.removeprefix('cloud:')} ({label})",
        "speech_output": answer.text,
        "result_data": {"model": ref, "commercial_tier": label},
    }


async def _run_candidate(candidate_type: str, item: Any, query: str, device: str, context: dict, route: dict, core_local: Callable) -> dict:
    if candidate_type == "local":
        return await core_local(item)
    return await _cloud(item, query, device, context, route)


def _candidates(models: List[str]) -> List[tuple]:
    out = []
    for cloud, group in groupby(models, key=is_cloud):
        names = list(group)
        if cloud:
            out.extend(("cloud", ref) for ref in names)
        else:
            out.append(("local", names))
    return out


async def ask(query: str, device: str, context: dict, route: dict, core_local: Callable) -> dict:
    pool = route.get("task_pool") if route.get("task_pool") in ("chat", "agent_tools", "vision", "deep_code", "voice_fast") else ("deep_code" if route.get("kind") == "deep" else "chat")
    from features.brain.free_router.failover_engine import configured_refs
    free_models = await configured_refs(pool)
    free_matrix_active = free_models is not None
    model_refs = route["models"]
    if free_matrix_active:
        local_models = [model for model in model_refs if not is_cloud(model)]
        model_refs = list(dict.fromkeys([*free_models, *local_models]))
        route = {**route, "models": model_refs, "free_matrix_active": True, "task_pool": pool}
    candidates = _candidates(model_refs)
    if not candidates:
        raise NoBrainAvailable("nessun cervello configurato")
    cortical_chain.set_mode(DEFAULT_MODE)
    engine = cortical_chain.engine()
    plan = engine.effective(query, cortical_chain.limbic).strategy
    if free_matrix_active:
        plan = replace(plan, candidates=1, pick="sequential", critic=False)
    parallel = plan.pick != "sequential" and min(plan.candidates, len(candidates)) > 1
    run_route = {**route, "remember": not parallel}

    def make_generator(ctype: str, target: Any) -> Generator:
        async def branch(q: str, ctx: Dict[str, Any], limbic: LimbicModulator) -> Dict[str, Any]:
            res = await _run_candidate(ctype, target, q, device, ctx, run_route, core_local)
            text = str(res.get("speech_output", ""))
            return {"text": text, "confidence": CONFIDENCE_OK if text and not text.lower().startswith("errore") else CONFIDENCE_BAD,
                    "raw_result": res, "kind": ctype, "target": target}
        return branch

    generators = [make_generator(ctype, target) for ctype, target in candidates]
    flow = engine.get_flow_stages(query, {"ui_lang": route.get("lang")}, cortical_chain.limbic, len(candidates))

    async def run(stages_left: list) -> Dict[str, Any]:
        if not stages_left:
            return await cortical_chain.execute_parallel_thought(query, context, generators, predict_user_impact, plan)
        step = stages_left[0]
        async with stages.stage(step["kind"], step["name"], step["detail"], step.get("label", "")):
            return await run(stages_left[1:])

    thought = await run(flow)
    raw = thought.get("raw_result")
    if not raw or not raw.get("speech_output"):
        for error in thought.get("errors") or []:
            store.event("WARN", f"Cervello non disponibile: {error}", "core")
        raise NoBrainAvailable("; ".join(thought.get("errors") or []) or "nessun cervello ha risposto")
    if parallel and thought.get("kind") == "cloud":
        conversation.remember(device, query, raw["speech_output"])
    raw["result_data"] = {**raw.get("result_data", {}), "limbic": thought.get("limbic_snapshot"), "latency_ms": thought.get("latency_ms"),
                          "mode": thought.get("mode"), "strategy": thought.get("strategy"), "score": thought.get("score"),
                          "candidates": {"launched": thought.get("candidates_launched"), "answered": thought.get("candidates_answered")}}
    return raw


__all__ = ["DEFAULT_MODE", "CONFIDENCE_BAD", "CONFIDENCE_OK", "CONFIDENCE_WEIGHT", "CRITIC_WEIGHT", "COMPLEXITY_WORDS", "CorticalBrainChain",
           "NoBrainAvailable", "ask", "cortical_chain", "valid"]
