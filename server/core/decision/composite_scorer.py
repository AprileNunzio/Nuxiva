import math
import random
from typing import Dict, List, Literal, Optional, Sequence
from server.core.decision.contracts import (
    BootstrapInterval,
    CompositeEvaluation,
    DecisionAxisScores,
    TaskTier,
)

TIER_WEIGHTS: Dict[TaskTier, float] = {
    TaskTier.EASY: 0.10,
    TaskTier.STANDARD: 0.20,
    TaskTier.JUDGE: 0.30,
    TaskTier.HARD: 0.40,
}

OFFICIAL_COST_CAP_PER_1K = 0.0646
OFFICIAL_MEDIAN_LATENCY_CAP_S = 1.23


def score_latency_seconds(latency_s: float) -> float:
    s_val = max(0.001, float(latency_s))
    if s_val <= 0.10:
        return 100.0
    raw = 100.0 - 20.0 * math.log10(s_val / 0.10)
    return round(max(0.0, min(100.0, raw)), 2)


def compute_speed_axis(
    p50_latency_ms: float,
    p95_latency_ms: float,
    self_hosted_unloaded: bool = False,
) -> float:
    p50_s = max(0.001, float(p50_latency_ms) / 1000.0)
    p95_s = max(p50_s, float(p95_latency_ms) / 1000.0)
    if self_hosted_unloaded:
        p50_s = (2.0 * p50_s) + 0.15
        p95_s = (2.0 * p95_s) + 0.15
    s50 = score_latency_seconds(p50_s)
    s95 = score_latency_seconds(p95_s)
    return round(0.50 * s50 + 0.50 * s95, 2)


def compute_cost_axis(
    cost_per_1k_decisions_usd: float,
    market_reference_floor_usd: float = 0.0,
) -> float:
    effective_cost = max(float(cost_per_1k_decisions_usd), float(market_reference_floor_usd))
    if effective_cost <= 0.001:
        return 100.0
    raw = 100.0 - 30.0 * math.log10(effective_cost / 0.001)
    return round(max(0.0, min(100.0, raw)), 2)


def compute_field_relative_overfit_multiplier(
    open_intelligence: float,
    sealed_intelligence: float,
    field_median_gap: float = 2.0,
) -> float:
    gap = float(open_intelligence) - float(sealed_intelligence)
    excess = gap - float(field_median_gap)
    if excess <= 8.0:
        return 1.0
    penalty = 1.0 - ((excess - 8.0) / 100.0)
    return round(max(0.0, min(1.0, penalty)), 4)


def compute_tier_weighted_intelligence(
    tier_competence_open: Dict[TaskTier, float],
    tier_competence_sealed: Dict[TaskTier, float],
    field_median_gap: float = 2.0,
) -> tuple[float, float, float]:
    def weighted_avg(scores: Dict[TaskTier, float]) -> float:
        if not scores:
            return 0.0
        total_w = 0.0
        acc = 0.0
        for tier, val in scores.items():
            w = TIER_WEIGHTS.get(tier, 0.25)
            acc += w * max(0.0, min(100.0, float(val)))
            total_w += w
        return acc / max(1e-9, total_w)

    i_open = weighted_avg(tier_competence_open)
    i_sealed = weighted_avg(tier_competence_sealed) if tier_competence_sealed else i_open
    raw_i = 0.50 * i_open + 0.50 * i_sealed
    multiplier = compute_field_relative_overfit_multiplier(i_open, i_sealed, field_median_gap)
    final_i = round(raw_i * multiplier, 2)
    return final_i, round(i_open - i_sealed, 2), multiplier


def compute_security_homeostasis_axis(
    zero_trust_pass_rate: float = 1.0,
    privacy_leak_risk: float = 0.0,
    limbic_vector: Optional[Sequence[float]] = None,
    guardrail_accuracy: float = 1.0,
) -> float:
    zt = max(0.0, min(1.0, float(zero_trust_pass_rate)))
    priv = max(0.0, min(1.0, 1.0 - float(privacy_leak_risk)))
    guard = max(0.0, min(1.0, float(guardrail_accuracy)))

    homeostasis = 1.0
    if limbic_vector and len(limbic_vector) >= 4:
        cortisol = max(0.0, min(1.0, float(limbic_vector[3])))
        noradrenaline = max(0.0, min(1.0, float(limbic_vector[1])))
        serotonin = max(0.0, min(1.0, float(limbic_vector[2])))
        stress_load = max(0.0, (0.6 * cortisol + 0.4 * noradrenaline) - (0.3 * serotonin))
        homeostasis = max(0.2, min(1.0, 1.0 - 0.5 * stress_load))

    score = 100.0 * (0.35 * zt + 0.30 * priv + 0.20 * guard + 0.15 * homeostasis)
    return round(max(0.0, min(100.0, score)), 2)


def weighted_harmonic_mean(values: Sequence[float], weights: Sequence[float]) -> float:
    if not values or len(values) != len(weights):
        return 0.0
    for val in values:
        if val <= 1e-6:
            return 0.0
    w_sum = sum(weights)
    if w_sum <= 0.0:
        return 0.0
    denom = sum((w / w_sum) / float(v) for v, w in zip(values, weights))
    if denom <= 0.0:
        return 0.0
    return round(1.0 / denom, 2)


def compute_quadratic_floor_gate(
    axes: DecisionAxisScores,
    intelligence_floor: float = 50.0,
    speed_floor: float = 50.0,
    cost_floor: float = 50.0,
    security_floor: float = 60.0,
    include_security_gate: bool = True,
) -> float:
    multiplier = 1.0
    if axes.intelligence < intelligence_floor and intelligence_floor > 0:
        ratio = max(0.0, axes.intelligence) / intelligence_floor
        multiplier *= ratio * ratio
    if axes.speed < speed_floor and speed_floor > 0:
        ratio = max(0.0, axes.speed) / speed_floor
        multiplier *= ratio * ratio
    if axes.cost < cost_floor and cost_floor > 0:
        ratio = max(0.0, axes.cost) / cost_floor
        multiplier *= ratio * ratio
    if include_security_gate and axes.security_homeostasis < security_floor and security_floor > 0:
        ratio = max(0.0, axes.security_homeostasis) / security_floor
        multiplier *= ratio * ratio
    return round(max(0.0, min(1.0, multiplier)), 6)


def compute_stratified_bootstrap_ci(
    strata_scores: Dict[str, List[float]],
    iterations: int = 400,
    seed: int = 42,
) -> BootstrapInterval:
    non_empty = {k: v for k, v in strata_scores.items() if v}
    if not non_empty:
        return BootstrapInterval(mean=0.0, ci_lower_95=0.0, ci_upper_95=0.0, std_error=0.0, samples=0)

    rng = random.Random(seed)
    replicates: List[float] = []
    total_items = sum(len(v) for v in non_empty.values())

    for _ in range(max(20, iterations)):
        stratum_means: List[float] = []
        for items in non_empty.values():
            n_k = len(items)
            sampled = [items[rng.randrange(n_k)] for _ in range(n_k)]
            stratum_means.append(sum(sampled) / n_k)
        replicates.append(sum(stratum_means) / len(stratum_means))

    replicates.sort()
    mean_val = sum(replicates) / len(replicates)
    variance = sum((x - mean_val) ** 2 for x in replicates) / max(1, len(replicates) - 1)
    std_err = math.sqrt(variance)
    low_idx = max(0, int(0.025 * len(replicates)))
    high_idx = min(len(replicates) - 1, int(0.975 * len(replicates)))

    return BootstrapInterval(
        mean=round(mean_val, 2),
        ci_lower_95=round(replicates[low_idx], 2),
        ci_upper_95=round(replicates[high_idx], 2),
        std_error=round(std_err, 3),
        samples=total_items,
    )


def evaluate_composite_score(
    axes: DecisionAxisScores,
    preset: Literal["A_BALANCED", "B_QUALITY", "C_PRODUCTION", "NUXIVA_5AXIS"] = "NUXIVA_5AXIS",
    open_sealed_gap: float = 0.0,
    overfit_penalty_multiplier: float = 1.0,
    cost_per_1k_usd: float = 0.01,
    p50_latency_s: float = 0.25,
    strata_scores: Optional[Dict[str, List[float]]] = None,
) -> CompositeEvaluation:
    if preset == "A_BALANCED":
        vals = [axes.intelligence, axes.calibration, axes.speed, axes.cost]
        weights = [0.25, 0.25, 0.25, 0.25]
        i_floor = 50.0
        use_sec = False
    elif preset == "B_QUALITY":
        vals = [axes.intelligence, axes.calibration, axes.speed, axes.cost]
        weights = [0.40, 0.20, 0.20, 0.20]
        i_floor = 50.0
        use_sec = False
    elif preset == "C_PRODUCTION":
        vals = [axes.intelligence, axes.calibration, axes.speed, axes.cost]
        weights = [0.25, 0.25, 0.25, 0.25]
        i_floor = 60.0
        use_sec = False
    else:
        vals = [
            axes.intelligence,
            axes.calibration,
            axes.speed,
            axes.cost,
            axes.security_homeostasis,
        ]
        weights = [0.30, 0.20, 0.15, 0.15, 0.20]
        i_floor = 55.0
        use_sec = True

    raw_hm = weighted_harmonic_mean(vals, weights)
    gate_mult = compute_quadratic_floor_gate(
        axes=axes,
        intelligence_floor=i_floor,
        speed_floor=50.0,
        cost_floor=50.0,
        security_floor=60.0,
        include_security_gate=use_sec,
    )
    composite = round(raw_hm * gate_mult, 2)
    capability = round(0.50 * axes.intelligence + 0.50 * axes.calibration, 2)
    within_caps = (
        float(cost_per_1k_usd) <= OFFICIAL_COST_CAP_PER_1K
        and float(p50_latency_s) <= OFFICIAL_MEDIAN_LATENCY_CAP_S
    )
    ci = compute_stratified_bootstrap_ci(strata_scores) if strata_scores else None

    return CompositeEvaluation(
        preset=preset,
        axes=axes,
        capability_score=capability,
        within_official_caps=within_caps,
        raw_harmonic_mean=raw_hm,
        floor_gate_multiplier=gate_mult,
        overfit_penalty_multiplier=overfit_penalty_multiplier,
        open_sealed_gap=open_sealed_gap,
        composite_score=composite,
        bootstrap_ci=ci,
    )
