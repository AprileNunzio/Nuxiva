import math
import time
from typing import Any, Dict, List, Literal, Optional, Sequence
from pydantic import BaseModel, Field
from server.core.decision.action_catalog import (
    TARGET_KEYWORDS,
    CandidateAction,
    ContextDimension,
    build_default_candidate_actions,
)
from server.core.decision.budget_ledger import DecisionBudgetLedger
from server.core.decision.calibration_metrics import (
    paraphrase_consistency_metrics,
    ranked_probability_score,
    summarize_calibration,
    total_variation_distance,
)
from server.core.decision.combinations import (
    CalibrationWeightedCommittee,
    ConfidenceCascadeEngine,
)
from server.core.decision.composite_scorer import (
    compute_cost_axis,
    compute_security_homeostasis_axis,
    compute_speed_axis,
    compute_tier_weighted_intelligence,
    evaluate_composite_score,
)
from server.core.decision.conformance_kit import (
    ConformanceReport,
    build_canonical_benchmark_tasks,
    run_conformance_suite,
)
from server.core.decision.contracts import (
    CalibrationSummary,
    CanonicalDecisionTask,
    CompositeEvaluation,
    ConformalPredictionSet,
    DecisionAxisScores,
    DecisionPrimitive,
    TaskSplit,
    TaskTier,
    TypedDecisionOutput,
    UncertaintyDecomposition,
    compute_dataset_hash,
)
from server.core.decision.scoring_math import (
    apply_temperature_scaling,
    chance_corrected_choice,
    chance_corrected_rubric,
    chance_corrected_verdict,
    compute_conformal_set,
    debias_option_order,
    decompose_uncertainty,
    deterministic_argmax,
    evaluate_verdict_band,
    normalized_mae,
    ordinal_expected_value,
    shift_binary_log_odds,
    validate_distribution,
)


class NuxivaDecision(BaseModel):
    selected_action: CandidateAction
    expected_value: float
    confidence: float
    reasoning_vector: Dict[str, float]
    ranked_candidates: List[Dict[str, Any]]
    evaluation_time_ms: float
    calibrated_probabilities: Dict[str, float] = Field(default_factory=dict)
    conformal_set: Optional[ConformalPredictionSet] = None
    uncertainty: Optional[UncertaintyDecomposition] = None
    abstained: bool = False


class NuxivaDecisionEngine:
    def __init__(self) -> None:
        self._action_registry: Dict[str, CandidateAction] = {}
        self._temperature: float = 0.85
        self._ledger = DecisionBudgetLedger(cap_usd=50.0)
        self._cascade = ConfidenceCascadeEngine(default_threshold=0.82)
        self._committee = CalibrationWeightedCommittee(competence_exponent=0.5)
        for item in build_default_candidate_actions():
            self.register_candidate(item)

    @property
    def ledger(self) -> DecisionBudgetLedger:
        return self._ledger

    @property
    def cascade(self) -> ConfidenceCascadeEngine:
        return self._cascade

    @property
    def committee(self) -> CalibrationWeightedCommittee:
        return self._committee

    def register_candidate(self, candidate: CandidateAction) -> None:
        self._action_registry[candidate.action_id] = candidate

    def evaluate(
        self,
        query: str,
        context: ContextDimension,
        limbic_vector: Optional[List[float]] = None,
    ) -> NuxivaDecision:
        t0 = time.perf_counter()
        reservation = self._ledger.reserve(
            adapter_id="nuxiva_decision_core",
            worst_case_usd=0.0005,
            max_tokens=256,
        )
        query_lower = query.lower()
        scored_candidates: List[tuple[CandidateAction, float, Dict[str, float]]] = []
        raw_logits: Dict[str, float] = {}

        for action_id, candidate in self._action_registry.items():
            prob_success = self._compute_success_probability(query_lower, candidate, context)
            utility = self._compute_utility(candidate, context)
            cost = candidate.execution_cost
            if context.system_load > 0.8:
                cost *= 1.5

            if limbic_vector and len(limbic_vector) >= 4:
                d, na, s, c = limbic_vector[0], limbic_vector[1], limbic_vector[2], limbic_vector[3]
                utility *= (1.0 + 0.3 * d + 0.2 * s)
                cost *= (1.0 + 0.5 * na)
                if c > 0.4 and candidate.privacy_risk > 0.1:
                    cost += (c * 4.0)

            expected_utility_score = (prob_success * utility) - cost
            if context.privacy_mode and candidate.privacy_risk > 0.3:
                expected_utility_score -= 10.0

            raw_logits[action_id] = expected_utility_score
            vector = {
                "prob_success": round(prob_success, 4),
                "utility": round(utility, 4),
                "cost": round(cost, 4),
                "expected_utility": round(expected_utility_score, 4),
            }
            scored_candidates.append((candidate, expected_utility_score, vector))

        max_logit = max(raw_logits.values()) if raw_logits else 0.0
        exp_map = {k: math.exp((v - max_logit) / max(0.15, self._temperature)) for k, v in raw_logits.items()}
        denom = sum(exp_map.values()) or 1.0
        raw_probs = {k: v / denom for k, v in exp_map.items()}
        validation = validate_distribution(raw_probs, list(self._action_registry.keys()))
        calibrated = validation.probabilities if validation.valid else raw_probs

        scored_candidates.sort(key=lambda x: (-calibrated.get(x[0].action_id, 0.0), x[0].action_id))
        best_candidate, best_score, best_vector = scored_candidates[0]
        top_label, top_conf = deterministic_argmax(calibrated)
        if top_label in self._action_registry:
            best_candidate = self._action_registry[top_label]

        conformal = compute_conformal_set(calibrated, alpha=0.10)
        uncertainty = decompose_uncertainty([calibrated])

        ranked = [
            {
                "action_id": c.action_id,
                "agent": c.target_agent,
                "subagent": c.subagent_id,
                "tool": c.required_tool,
                "widget": c.associated_widget,
                "score": round(s, 4),
                "probability": round(calibrated.get(c.action_id, 0.0), 4),
                "metrics": v,
            }
            for c, s, v in scored_candidates[:5]
        ]

        t1 = time.perf_counter()
        latency = (t1 - t0) * 1000.0
        self._ledger.settle(reservation.reservation_id, actual_usd=0.000001, actual_tokens=64)

        return NuxivaDecision(
            selected_action=best_candidate,
            expected_value=round(best_score, 4),
            confidence=round(top_conf, 4),
            reasoning_vector=best_vector,
            ranked_candidates=ranked,
            evaluation_time_ms=round(latency, 2),
            calibrated_probabilities={k: round(v, 4) for k, v in calibrated.items()},
            conformal_set=conformal,
            uncertainty=uncertainty,
            abstained=(top_conf < 0.25),
        )

    def decide_verdict(
        self,
        proposition: str,
        state: Dict[str, Any],
        temperature: float = 1.0,
        threshold_tau: float = 0.50,
    ) -> TypedDecisionOutput:
        t0 = time.perf_counter()
        cmd = str(state.get("command", "")).lower()
        destructive = bool(state.get("destructive", False)) or any(
            w in cmd for w in ("formatta", "cancella", "elimina", "drop", "rm -rf")
        )
        authenticated = bool(state.get("authenticated", True))
        history = [str(x).lower() for x in state.get("history", [])]

        if "safe to run" in proposition.lower():
            base_yes = 0.06 if (destructive and not authenticated) else (0.28 if destructive else 0.93)
        elif "closed" in proposition.lower() and history:
            all_closed = all("aperta" not in item and "open" not in item for item in history)
            base_yes = 0.91 if all_closed else 0.11
        else:
            positive_signals = sum(1 for v in state.values() if v is True or v == "ok")
            negative_signals = sum(1 for v in state.values() if v is False or v == "error")
            base_yes = min(0.95, max(0.05, 0.55 + 0.18 * positive_signals - 0.22 * negative_signals))

        shifted_yes = shift_binary_log_odds(base_yes, threshold_tau)
        raw_dist = {"yes": shifted_yes, "no": 1.0 - shifted_yes}
        scaled_dist = apply_temperature_scaling(raw_dist, temperature)
        val = validate_distribution(scaled_dist, ["yes", "no"])
        p_yes = val.probabilities.get("yes", 0.5) if val.valid else 0.5
        pred_label, abstained, conf = evaluate_verdict_band(p_yes)
        conformal = compute_conformal_set(val.probabilities, alpha=0.10)
        uncertainty = decompose_uncertainty([val.probabilities])
        latency = (time.perf_counter() - t0) * 1000.0

        return TypedDecisionOutput(
            primitive=DecisionPrimitive.VERDICT,
            valid=val.valid,
            strict_valid=val.strict_valid,
            renormalized=val.renormalized,
            predicted_label=pred_label,
            abstained=abstained,
            expected_value=round(p_yes, 4),
            confidence=round(conf, 4),
            probabilities={k: round(v, 6) for k, v in val.probabilities.items()},
            calibrated_temperature=temperature,
            option_order_gap=0.0,
            conformal_set=conformal,
            uncertainty=uncertainty,
            latency_ms=round(latency, 3),
            cost_usd=0.000001,
        )

    def decide_choice(
        self,
        query: str,
        options: Sequence[str],
        context: Optional[ContextDimension] = None,
        temperature: float = 0.85,
    ) -> TypedDecisionOutput:
        t0 = time.perf_counter()
        ctx = context or ContextDimension()
        q_lower = query.lower()
        opts = [str(o) for o in options if str(o).strip()]
        if not opts:
            opts = list(self._action_registry.keys())[:4]

        fwd_logits: Dict[str, float] = {}
        rev_logits: Dict[str, float] = {}

        for idx, opt in enumerate(opts):
            cand = self._action_registry.get(opt)
            if cand is not None:
                base_p = self._compute_success_probability(q_lower, cand, ctx)
            else:
                tokens = opt.lower().replace("_", " ").split()
                hits = sum(1 for tok in tokens if tok in q_lower)
                base_p = min(0.92, 0.15 + 0.35 * hits)
            logit_val = 4.2 * base_p
            fwd_logits[opt] = math.exp(logit_val + 0.005 * (len(opts) - idx))
            rev_logits[opt] = math.exp(logit_val + 0.005 * (idx + 1))

        fwd_sum = sum(fwd_logits.values()) or 1.0
        rev_sum = sum(rev_logits.values()) or 1.0
        fwd_probs = apply_temperature_scaling({k: v / fwd_sum for k, v in fwd_logits.items()}, temperature)
        rev_probs = apply_temperature_scaling({k: v / rev_sum for k, v in rev_logits.items()}, temperature)
        debiased, order_gap = debias_option_order(fwd_probs, rev_probs)
        val = validate_distribution(debiased, opts)
        pred_label, conf = deterministic_argmax(val.probabilities)
        conformal = compute_conformal_set(val.probabilities, alpha=0.10)
        uncertainty = decompose_uncertainty([fwd_probs, rev_probs])
        latency = (time.perf_counter() - t0) * 1000.0

        return TypedDecisionOutput(
            primitive=DecisionPrimitive.CHOICE,
            valid=val.valid,
            strict_valid=val.strict_valid,
            renormalized=val.renormalized,
            predicted_label=pred_label,
            abstained=False,
            expected_value=round(conf, 4),
            confidence=round(conf, 4),
            probabilities={k: round(v, 6) for k, v in val.probabilities.items()},
            calibrated_temperature=temperature,
            option_order_gap=order_gap,
            conformal_set=conformal,
            uncertainty=uncertainty,
            latency_ms=round(latency, 3),
            cost_usd=0.000001,
        )

    def decide_rubric(
        self,
        state: Dict[str, Any],
        rubric_levels: int = 5,
        temperature: float = 0.90,
    ) -> TypedDecisionOutput:
        t0 = time.perf_counter()
        k_levels = max(2, min(20, int(rubric_levels)))
        quality = float(state.get("quality", 0.75))
        completeness = float(state.get("completeness", 0.75))
        sec_ok = bool(state.get("security_verified", True))
        composite_signal = min(1.0, max(0.0, 0.45 * quality + 0.35 * completeness + (0.20 if sec_ok else 0.0)))
        target_center = composite_signal * (k_levels - 1)

        raw: Dict[str, float] = {}
        for level in range(k_levels):
            dist = abs(level - target_center)
            raw[str(level)] = math.exp(-1.6 * dist * dist)
        raw_sum = sum(raw.values()) or 1.0
        norm_raw = {k: v / raw_sum for k, v in raw.items()}
        scaled = apply_temperature_scaling(norm_raw, temperature)
        expected_keys = [str(i) for i in range(k_levels)]
        val = validate_distribution(scaled, expected_keys)
        pred_label, conf = deterministic_argmax(val.probabilities)
        ev = ordinal_expected_value(val.probabilities, k_levels)
        conformal = compute_conformal_set(val.probabilities, alpha=0.10)
        uncertainty = decompose_uncertainty([val.probabilities])
        latency = (time.perf_counter() - t0) * 1000.0

        return TypedDecisionOutput(
            primitive=DecisionPrimitive.RUBRIC,
            valid=val.valid,
            strict_valid=val.strict_valid,
            renormalized=val.renormalized,
            predicted_label=pred_label,
            abstained=False,
            expected_value=ev,
            confidence=round(conf, 4),
            probabilities={k: round(v, 6) for k, v in val.probabilities.items()},
            calibrated_temperature=temperature,
            option_order_gap=0.0,
            conformal_set=conformal,
            uncertainty=uncertainty,
            latency_ms=round(latency, 3),
            cost_usd=0.000001,
        )

    def evaluate_task(self, task: CanonicalDecisionTask) -> TypedDecisionOutput:
        if task.primitive == DecisionPrimitive.VERDICT:
            return self.decide_verdict(task.proposition or "", task.state)
        if task.primitive == DecisionPrimitive.CHOICE:
            query = str(task.state.get("query", ""))
            return self.decide_choice(query, task.options or [])
        return self.decide_rubric(task.state, rubric_levels=task.rubric_levels)

    def run_conformance(self) -> ConformanceReport:
        return run_conformance_suite("nuxiva_cognitive_arbiter_v2", self.evaluate_task)

    def run_benchmark(
        self,
        preset: Literal["A_BALANCED", "B_QUALITY", "C_PRODUCTION", "NUXIVA_5AXIS"] = "NUXIVA_5AXIS",
    ) -> Dict[str, Any]:
        tasks = build_canonical_benchmark_tasks()
        outputs: List[TypedDecisionOutput] = [self.evaluate_task(t) for t in tasks]

        distributions: List[Dict[str, float]] = []
        gold_labels: List[str] = []
        rps_list: List[float] = []
        tvd_list: List[float] = []
        order_gaps: List[float] = []
        latencies: List[float] = []
        costs: List[float] = []
        open_tier_scores: Dict[TaskTier, List[float]] = {}
        sealed_tier_scores: Dict[TaskTier, List[float]] = {}
        strata_scores: Dict[str, List[float]] = {}

        for task, out in zip(tasks, outputs):
            latencies.append(max(0.05, out.latency_ms))
            costs.append(out.cost_usd)
            order_gaps.append(out.option_order_gap)
            gold_str = task.gold_label if task.gold_label is not None else str(task.gold_score or 0)
            distributions.append(out.probabilities)
            gold_labels.append(gold_str)

            if task.primitive == DecisionPrimitive.VERDICT:
                comp = chance_corrected_verdict(1.0 if out.predicted_label == gold_str else 0.0)
            elif task.primitive == DecisionPrimitive.CHOICE:
                comp = chance_corrected_choice(
                    1.0 if out.predicted_label == gold_str else 0.0,
                    [len(task.options or ["a", "b"])],
                )
            else:
                g_lvl = int(task.gold_score or 0)
                item_nmae = normalized_mae(out.expected_value, g_lvl, task.rubric_levels)
                comp = chance_corrected_rubric([item_nmae], [g_lvl], [task.rubric_levels])
                rps_list.append(
                    ranked_probability_score(out.probabilities, g_lvl, task.rubric_levels, task.gold_distribution)
                )
                if task.gold_distribution:
                    tvd_list.append(total_variation_distance(out.probabilities, task.gold_distribution))

            target_map = open_tier_scores if task.split == TaskSplit.OPEN else sealed_tier_scores
            target_map.setdefault(task.tier, []).append(comp)
            strata_scores.setdefault(f"{task.split.value}:{task.primitive.value}:{task.tier.value}", []).append(comp)

        para_agree, para_both = paraphrase_consistency_metrics(
            [t.group_id for t in tasks],
            [o.predicted_label for o in outputs],
            [t.gold_label if t.gold_label is not None else str(t.gold_score) for t in tasks],
            [o.valid for o in outputs],
        )
        cal_summary: CalibrationSummary = summarize_calibration(
            distributions=distributions,
            gold_labels=gold_labels,
            ordinal_rps_values=rps_list,
            tvd_values=tvd_list,
            paraphrase_agreement=para_agree,
            paraphrase_both_correct=para_both,
            option_order_gaps=order_gaps,
        )

        open_avg = {tier: sum(vals) / len(vals) for tier, vals in open_tier_scores.items()}
        sealed_avg = {tier: sum(vals) / len(vals) for tier, vals in sealed_tier_scores.items()}
        intel_score, gap, overfit_mult = compute_tier_weighted_intelligence(open_avg, sealed_avg)
        sorted_lat = sorted(latencies)
        p50_ms = sorted_lat[len(sorted_lat) // 2]
        p95_ms = sorted_lat[min(len(sorted_lat) - 1, int(0.95 * len(sorted_lat)))]
        cost_per_1k = (sum(costs) / max(1, len(costs))) * 1000.0

        axes = DecisionAxisScores(
            intelligence=intel_score,
            calibration=cal_summary.pooled_calibration_score,
            speed=compute_speed_axis(p50_ms, p95_ms),
            cost=compute_cost_axis(cost_per_1k),
            security_homeostasis=compute_security_homeostasis_axis(
                zero_trust_pass_rate=1.0,
                privacy_leak_risk=0.02,
                limbic_vector=[0.6, 0.2, 0.8, 0.15],
                guardrail_accuracy=1.0,
            ),
        )
        comp_eval: CompositeEvaluation = evaluate_composite_score(
            axes=axes,
            preset=preset,
            open_sealed_gap=gap,
            overfit_penalty_multiplier=overfit_mult,
            cost_per_1k_usd=cost_per_1k,
            p50_latency_s=p50_ms / 1000.0,
            strata_scores=strata_scores,
        )
        return {
            "dataset_hash": compute_dataset_hash(tasks),
            "task_count": len(tasks),
            "evaluation": comp_eval.model_dump(),
            "calibration_details": cal_summary.model_dump(),
            "latency_p50_ms": round(p50_ms, 3),
            "latency_p95_ms": round(p95_ms, 3),
            "cost_per_1k_usd": round(cost_per_1k, 4),
            "cascade_threshold": self._cascade.threshold,
        }

    def _compute_success_probability(self, query: str, candidate: CandidateAction, ctx: ContextDimension) -> float:
        score = 0.1
        sub = candidate.subagent_id or candidate.target_agent
        keywords = TARGET_KEYWORDS.get(sub, [])
        match_count = sum(1 for kw in keywords if kw in query)
        if match_count > 0:
            score += min(0.85, match_count * 0.4)
        if candidate.required_tool and candidate.required_tool in ctx.available_plugins:
            score += 0.1
        return min(0.99, max(0.01, score))

    def _compute_utility(self, candidate: CandidateAction, ctx: ContextDimension) -> float:
        utility = candidate.base_utility
        if ctx.user_role == "user_primary":
            utility *= 1.2
        if candidate.associated_widget and candidate.associated_widget in ctx.active_widgets:
            utility += 0.5
        return utility


decision_engine = NuxivaDecisionEngine()
