import os
from typing import Any, Dict
from server.core.decision.contracts import DecisionPrimitive
from server.core.decision.decision_engine import decision_engine
from server.core.orchestrator.brain_routing import configured_ollama_url, preferred_brain_for
from server.features.cognitive_arbiter.schemas import (
    BenchmarkSuiteRequest,
    CascadeDecisionRequest,
    CommitteeDecisionRequest,
    ThresholdTuneRequest,
    TypedDecisionRequest,
)
from server.shared.utils.text_sanitizer import TextSanitizer


class CognitiveArbiterService:
    def __init__(self) -> None:
        self._sanitizer = TextSanitizer()

    def _resolve_live_runtime(
        self,
        override_model: str = "",
        override_provider: str = "",
        override_url: str = "",
        override_sys1: str = "",
        override_sys2: str = "",
    ) -> Dict[str, str]:
        env_model = os.environ.get("NUXIVA_LLM_MODEL", "").strip()
        env_fast = os.environ.get("NUXIVA_LLM_FAST_MODEL", "").strip()
        env_deep = os.environ.get("NUXIVA_LLM_DEEP_ORDER", "").strip()
        env_brain = os.environ.get("NUXIVA_BRAIN", "").strip()
        env_url = os.environ.get("NUXIVA_OLLAMA_URL", "").strip() or configured_ollama_url()

        active_model = (
            self._sanitizer.sanitize_plain_text(override_model)[:120]
            or env_model
            or preferred_brain_for("system1_router")
            or "dynamic_runtime_model"
        )
        sys1_model = (
            self._sanitizer.sanitize_plain_text(override_sys1)[:120]
            or env_fast
            or preferred_brain_for("system1_router")
            or active_model
        )
        sys2_model = (
            self._sanitizer.sanitize_plain_text(override_sys2)[:120]
            or (env_deep.split(",")[0].strip() if env_deep else "")
            or preferred_brain_for("system2_engine")
            or active_model
        )
        base_url = self._sanitizer.sanitize_plain_text(override_url)[:200] or env_url
        if override_provider:
            provider = self._sanitizer.sanitize_plain_text(override_provider)[:40]
        elif active_model.startswith("cloud:") or env_brain == "cloud":
            provider = "api_key"
        elif base_url and not any(h in base_url for h in ("127.0.0.1", "localhost", "[::1]")):
            provider = "ollama_remote"
        else:
            provider = "ollama_local"

        return {
            "active_model": active_model,
            "provider": provider,
            "base_url": base_url,
            "system1_model": sys1_model,
            "system2_model": sys2_model,
        }

    def get_overview(self) -> Dict[str, Any]:
        runtime = self._resolve_live_runtime()
        benchmark = decision_engine.run_benchmark(preset="NUXIVA_5AXIS")
        conformance = decision_engine.run_conformance()
        ledger = decision_engine.ledger.summary()
        return {
            "engine_version": "2.0.0-nuxiva-arbiter",
            "cascade_threshold": decision_engine.cascade.threshold,
            "active_runtime": runtime,
            "benchmark": benchmark,
            "conformance": conformance.model_dump(),
            "ledger": ledger,
        }

    def execute_typed_decision(self, req: TypedDecisionRequest) -> Dict[str, Any]:
        runtime = self._resolve_live_runtime(req.active_model, req.provider, req.base_url)
        clean_query = self._sanitizer.sanitize_plain_text(req.query) if req.query else ""
        clean_prop = self._sanitizer.sanitize_plain_text(req.proposition) if req.proposition else ""
        clean_options = [self._sanitizer.sanitize_plain_text(opt)[:80] for opt in req.options if opt]

        reservation = decision_engine.ledger.reserve(
            adapter_id=f"{runtime['provider']}:{runtime['active_model']}:{req.primitive.value}",
            worst_case_usd=0.0005 if runtime["provider"] == "api_key" else 0.0,
            max_tokens=512,
        )

        if req.primitive == DecisionPrimitive.VERDICT:
            out = decision_engine.decide_verdict(
                proposition=clean_prop or clean_query or "The requested operation is safe to run.",
                state=req.state,
                temperature=req.temperature,
                threshold_tau=req.threshold_tau,
            )
        elif req.primitive == DecisionPrimitive.RUBRIC:
            out = decision_engine.decide_rubric(
                state=req.state or {"quality": 0.85, "completeness": 0.90, "security_verified": True},
                rubric_levels=req.rubric_levels,
                temperature=req.temperature,
            )
        else:
            out = decision_engine.decide_choice(
                query=clean_query or "select_optimal_action",
                options=clean_options,
                temperature=req.temperature,
            )

        decision_engine.ledger.settle(
            reservation_id=reservation.reservation_id,
            actual_usd=out.cost_usd if runtime["provider"] == "api_key" else 0.0,
            actual_tokens=96,
        )
        dumped = out.model_dump()
        dumped["active_runtime"] = runtime
        return dumped

    def execute_cascade(self, req: CascadeDecisionRequest) -> Dict[str, Any]:
        runtime = self._resolve_live_runtime(
            req.active_model,
            req.provider,
            req.base_url,
            req.system1_model,
            req.system2_model,
        )
        clean_query = self._sanitizer.sanitize_plain_text(req.query)
        clean_options = [self._sanitizer.sanitize_plain_text(o)[:80] for o in req.options if o]
        if req.escalation_threshold is not None:
            decision_engine.cascade.set_threshold(req.escalation_threshold)

        fast_out = decision_engine.decide_choice(
            query=clean_query,
            options=clean_options,
            temperature=1.25,
        )

        def deep_eval():
            return decision_engine.decide_choice(
                query=clean_query,
                options=clean_options,
                temperature=0.65,
            )

        outcome = decision_engine.cascade.execute_cascade(
            fast_output=fast_out,
            deep_provider=deep_eval,
            require_singleton_conformal=req.require_singleton_conformal,
        )
        dumped = outcome.model_dump()
        chosen_model = runtime["system2_model"] if outcome.escalated else runtime["system1_model"]
        dumped["selected_tier"] = f"{outcome.selected_tier} ({chosen_model} • {runtime['provider']})"
        dumped["active_runtime"] = runtime
        return dumped

    def execute_committee(self, req: CommitteeDecisionRequest) -> Dict[str, Any]:
        clean_labels = [self._sanitizer.sanitize_plain_text(lbl)[:80] for lbl in req.expected_labels]
        tuples = [
            (
                self._sanitizer.sanitize_plain_text(m.member_id)[:80],
                m.probabilities,
                m.calibration_score,
                m.intelligence_score,
            )
            for m in req.members
        ]
        outcome = decision_engine.committee.combine(
            members=tuples,
            expected_labels=clean_labels,
            conformal_alpha=req.conformal_alpha,
        )
        return outcome.model_dump()

    def run_benchmark(self, req: BenchmarkSuiteRequest) -> Dict[str, Any]:
        runtime = self._resolve_live_runtime(req.active_model, req.provider, req.base_url)
        res = decision_engine.run_benchmark(preset=req.preset)
        res["active_runtime"] = runtime
        return res

    def run_conformance(self) -> Dict[str, Any]:
        return decision_engine.run_conformance().model_dump()

    def update_threshold(self, req: ThresholdTuneRequest) -> Dict[str, Any]:
        updated = decision_engine.cascade.set_threshold(req.threshold)
        return {"cascade_threshold": updated}


cognitive_arbiter_service = CognitiveArbiterService()
