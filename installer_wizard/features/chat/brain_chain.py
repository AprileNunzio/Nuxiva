import asyncio
import time
from itertools import groupby
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx
from state import store
from tasks import background

from features.brain.brains import brains
from features.brain.components import (
    LimbicModulator,
    SpikingNeuron,
)
from features.brain.residency import touch
from features.brain.trace import trace
from features.cloud import conversation
from features.cloud.catalog import is_cloud
from features.cloud.client import CloudError
from features.twin.simulator import predict_user_impact


REASONING_PROFILES: Dict[str, Dict[str, Any]] = {
    "nuxiva-4.2-legacy": {
        "parallel_branches": 1,
        "mcts_depth": 1,
        "ignition_threshold": 0.50,
        "timeout_s": 8.0,
        "use_limbic": False,
        "use_twin_critic": False,
    },
    "nuxiva-5.0-fast": {
        "parallel_branches": 3,
        "mcts_depth": 1,
        "ignition_threshold": 0.72,
        "timeout_s": 0.45,
        "use_limbic": True,
        "use_twin_critic": False,
    },
    "nuxiva-5.0-empathetic": {
        "parallel_branches": 6,
        "mcts_depth": 2,
        "ignition_threshold": 0.78,
        "timeout_s": 1.8,
        "use_limbic": True,
        "use_twin_critic": True,
    },
    "nuxiva-6.0-pro": {
        "parallel_branches": 8,
        "mcts_depth": 3,
        "ignition_threshold": 0.85,
        "timeout_s": 3.5,
        "use_limbic": True,
        "use_twin_critic": True,
    },
    "nuxiva-6.5-ultra": {
        "parallel_branches": 16,
        "mcts_depth": 5,
        "ignition_threshold": 0.92,
        "timeout_s": 7.5,
        "use_limbic": True,
        "use_twin_critic": True,
    },
    "nuxiva-6.5-auto": {
        "parallel_branches": 8,
        "mcts_depth": 3,
        "ignition_threshold": 0.82,
        "timeout_s": 3.0,
        "use_limbic": True,
        "use_twin_critic": True,
    },
}


class NoBrainAvailable(RuntimeError):
    pass


class CorticalBrainChain:
    def __init__(self) -> None:
        self.limbic = LimbicModulator()
        self.neurons: Dict[str, SpikingNeuron] = {}
        self.active_mode: str = "nuxiva-6.5-auto"

    def set_mode(self, mode_id: str) -> str:
        if mode_id in REASONING_PROFILES:
            self.active_mode = mode_id
        return self.active_mode

    def resolve_effective_profile(self, query: str) -> Dict[str, Any]:
        if self.active_mode != "nuxiva-6.5-auto":
            return REASONING_PROFILES.get(self.active_mode, REASONING_PROFILES["nuxiva-6.0-pro"])
        complexity = min(1.0, len(query.split()) / 45.0)
        if self.limbic.noradrenaline > 0.75 and complexity < 0.3:
            return REASONING_PROFILES["nuxiva-5.0-fast"]
        if abs(self.limbic.valence) > 0.65:
            return REASONING_PROFILES["nuxiva-5.0-empathetic"]
        if complexity > 0.65:
            return REASONING_PROFILES["nuxiva-6.5-ultra"]
        return REASONING_PROFILES["nuxiva-6.0-pro"]

    def register_cortical_column(self, neuron: SpikingNeuron) -> None:
        self.neurons[neuron.neuron_id] = neuron

    async def execute_parallel_thought(
        self,
        query: str,
        context: Dict[str, Any],
        branch_generators: List[Callable[[str, Dict[str, Any], LimbicModulator], Awaitable[Dict[str, Any]]]],
        critic_fn: Optional[Callable[[Dict[str, Any], LimbicModulator], Awaitable[float]]] = None,
    ) -> Dict[str, Any]:
        started = time.perf_counter()
        profile = self.resolve_effective_profile(query)
        max_branches = self.limbic.parallel_branch_budget(profile["parallel_branches"])
        selected_generators = branch_generators[:max_branches]
        if not selected_generators:
            return {"text": "", "confidence": 0.0, "mode": self.active_mode, "latency_ms": 0.0}

        ignition_threshold = float(profile["ignition_threshold"])
        mcts_depth = int(profile["mcts_depth"])
        winner: Optional[Dict[str, Any]] = None
        best_candidate: Optional[Dict[str, Any]] = None
        best_score: float = -1.0
        ignition_event = asyncio.Event()
        lock = asyncio.Lock()

        async def run_branch(
            idx: int,
            gen_fn: Callable[[str, Dict[str, Any], LimbicModulator], Awaitable[Dict[str, Any]]],
        ) -> None:
            nonlocal winner, best_candidate, best_score
            current_context = dict(context)
            cumulative_score = 0.0
            for step in range(mcts_depth):
                if ignition_event.is_set():
                    return
                try:
                    candidate = await gen_fn(query, current_context, self.limbic)
                except Exception:
                    return
                raw_conf = float(candidate.get("confidence", 0.6))
                if critic_fn is not None and profile["use_twin_critic"]:
                    try:
                        critic_score = await critic_fn(candidate, self.limbic)
                    except Exception:
                        critic_score = 0.5
                    step_score = (raw_conf * 0.55) + (critic_score * 0.45)
                else:
                    step_score = raw_conf
                cumulative_score = ((cumulative_score * step) + step_score) / (step + 1)
                candidate["branch_id"] = idx
                candidate["mcts_step"] = step + 1
                candidate["score"] = cumulative_score
                async with lock:
                    if cumulative_score > best_score:
                        best_score = cumulative_score
                        best_candidate = candidate
                    if cumulative_score >= ignition_threshold and winner is None:
                        winner = candidate
                        ignition_event.set()
                        return
                if step_score < (ignition_threshold * 0.45):
                    return
                current_context["latent_refinement"] = candidate.get("text", "")

        tasks = [
            asyncio.create_task(run_branch(i, gen))
            for i, gen in enumerate(selected_generators)
        ]
        done, pending = await asyncio.wait(
            tasks,
            timeout=float(profile["timeout_s"]),
            return_when=asyncio.FIRST_COMPLETED if max_branches == 1 else asyncio.ALL_COMPLETED,
        )
        for p in pending:
            p.cancel()
        final_thought = winner if winner is not None else (best_candidate or {"text": "", "score": 0.0})
        final_thought["mode"] = self.active_mode
        final_thought["parallel_branches_launched"] = len(selected_generators)
        final_thought["latency_ms"] = round((time.perf_counter() - started) * 1000.0, 2)
        final_thought["limbic_snapshot"] = {
            "valence": round(self.limbic.valence, 3),
            "arousal": round(self.limbic.arousal, 3),
            "dopamine": round(self.limbic.dopamine, 3),
            "noradrenaline": round(self.limbic.noradrenaline, 3),
            "serotonin": round(self.limbic.serotonin, 3),
            "cortisol": round(self.limbic.cortisol, 3),
        }
        return final_thought


cortical_chain = CorticalBrainChain()


def _label(kind: str) -> str:
    return "Nuxiva 5.0 Veloce (5.0-flash)" if kind == "chat" else "Nuxiva 5.0 Pro Ragionamento (5.0-pro)"


async def _cloud(ref: str, query: str, device: str, context: dict, route: dict) -> dict:
    started = time.time()
    call = trace.begin("conversation", route["reason"], route["models"])
    trace.attempt(call, ref)
    try:
        answer = await conversation.reply(ref, query, device, context, route["max_tokens"])
    except CloudError as exc:
        brains.record(ref, (time.time() - started) * 1000, False, route["kind"])
        trace.abort(call, str(exc))
        raise
    brains.record(ref, answer.ms, True, route["kind"])
    trace.finish(call, ref, answer.ms, answer.text)
    background(touch(ref))
    return {
        "agent_id": f"nuxiva_cloud · {ref.removeprefix('cloud:')} ({_label(route['kind'])})",
        "speech_output": answer.text,
        "result_data": {"model": ref, "commercial_tier": _label(route["kind"])},
    }


async def _run_candidate(candidate_type: str, item: Any, query: str, device: str, context: dict, route: dict, core_local: Callable) -> dict:
    if candidate_type == "local":
        return await core_local(item)
    return await _cloud(item, query, device, context, route)


async def ask(query: str, device: str, context: dict, route: dict, core_local: Callable) -> dict:
    candidates = []
    for cloud, group in groupby(route["models"], key=is_cloud):
        names = list(group)
        if not cloud:
            candidates.append(("local", names))
        else:
            for ref in names:
                candidates.append(("cloud", ref))

    if not candidates:
        raise NoBrainAvailable("nessun cervello configurato")

    mode_id = route.get("reasoning_mode") or ("nuxiva-5.0-fast" if route.get("kind") == "chat" else "nuxiva-6.0-pro")
    cortical_chain.set_mode(mode_id)

    branch_generators: List[Callable[[str, Dict[str, Any], LimbicModulator], Awaitable[Dict[str, Any]]]] = []
    for ctype, target in candidates:
        def make_generator(ct: str, tg: Any):
            async def branch_gen(q: str, ctx: Dict[str, Any], limbic: LimbicModulator) -> Dict[str, Any]:
                res = await _run_candidate(ct, tg, q, device, ctx, route, core_local)
                text = str(res.get("speech_output", ""))
                conf = 0.88 if text and not text.lower().startswith("errore") else 0.35
                return {
                    "text": text,
                    "confidence": conf,
                    "raw_result": res,
                    "speech_output": text,
                    "agent_id": res.get("agent_id", "cortical_node"),
                    "result_data": res.get("result_data", {}),
                }
            return branch_gen
        branch_generators.append(make_generator(ctype, target))

    final_thought = await cortical_chain.execute_parallel_thought(
        query,
        context,
        branch_generators,
        critic_fn=predict_user_impact,
    )

    raw = final_thought.get("raw_result")
    if raw and raw.get("speech_output"):
        raw["result_data"] = {
            **raw.get("result_data", {}),
            "limbic": final_thought.get("limbic_snapshot"),
            "latency_ms": final_thought.get("latency_ms"),
            "mode": final_thought.get("mode"),
        }
        return raw

    if final_thought.get("text"):
        return {
            "agent_id": f"cortical · {final_thought.get('mode', 'nuxiva-6.5-auto')}",
            "speech_output": final_thought.get("text"),
            "result_data": {
                "limbic": final_thought.get("limbic_snapshot"),
                "latency_ms": final_thought.get("latency_ms"),
                "mode": final_thought.get("mode"),
            },
        }

    errors = []
    for ctype, target in candidates:
        try:
            return await _run_candidate(ctype, target, query, device, context, route, core_local)
        except (httpx.HTTPError, ValueError) as exc:
            errors.append(f"locale: {type(exc).__name__}")
            store.event("WARN", f"Modello locale non disponibile: {exc}", "core")
        except CloudError as exc:
            errors.append(str(exc)[:160])
            store.event("WARN", f"Cervello cloud non disponibile: {exc}", "cloud")

    raise NoBrainAvailable("; ".join(errors) or "nessun cervello disponibile")
