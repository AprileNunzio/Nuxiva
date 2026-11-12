import math
from typing import Dict, List, Optional, Sequence, Tuple
from server.core.decision.contracts import (
    ConformalPredictionSet,
    DistributionValidation,
    UncertaintyDecomposition,
)

SUM_TOL = 1e-3
RENORM_TOL = 2e-2
VERDICT_LOW_BAND = 0.20
VERDICT_HIGH_BAND = 0.80
EPS = 1e-12


def validate_distribution(
    raw_probs: Dict[str, float],
    expected_labels: Sequence[str],
) -> DistributionValidation:
    if not raw_probs or not expected_labels:
        return DistributionValidation(
            valid=False,
            strict_valid=False,
            renormalized=False,
            probabilities={},
            raw_sum=0.0,
            error_reason="empty_distribution_or_labels",
        )

    expected_set = set(expected_labels)
    if set(raw_probs.keys()) != expected_set:
        return DistributionValidation(
            valid=False,
            strict_valid=False,
            renormalized=False,
            probabilities={},
            raw_sum=0.0,
            error_reason="label_key_mismatch",
        )

    cleaned: Dict[str, float] = {}
    for label in expected_labels:
        val = float(raw_probs[label])
        if not math.isfinite(val) or val < -1e-9 or val > 1.0 + RENORM_TOL:
            return DistributionValidation(
                valid=False,
                strict_valid=False,
                renormalized=False,
                probabilities={},
                raw_sum=0.0,
                error_reason="non_finite_or_out_of_bounds_probability",
            )
        cleaned[label] = max(0.0, val)

    total = sum(cleaned.values())
    if total <= 0.0:
        return DistributionValidation(
            valid=False,
            strict_valid=False,
            renormalized=False,
            probabilities={},
            raw_sum=total,
            error_reason="zero_probability_mass",
        )

    deviation = abs(total - 1.0)
    if deviation <= SUM_TOL:
        normalized = {k: cleaned[k] / total for k in expected_labels}
        return DistributionValidation(
            valid=True,
            strict_valid=True,
            renormalized=False,
            probabilities=normalized,
            raw_sum=round(total, 6),
        )

    if deviation <= RENORM_TOL:
        normalized = {k: cleaned[k] / total for k in expected_labels}
        return DistributionValidation(
            valid=True,
            strict_valid=False,
            renormalized=True,
            probabilities=normalized,
            raw_sum=round(total, 6),
        )

    return DistributionValidation(
        valid=False,
        strict_valid=False,
        renormalized=False,
        probabilities={},
        raw_sum=round(total, 6),
        error_reason="sum_outside_renormalization_tolerance",
    )


def deterministic_argmax(probabilities: Dict[str, float]) -> Tuple[str, float]:
    if not probabilities:
        return "", 0.0
    ordered = sorted(probabilities.items(), key=lambda kv: (-kv[1], str(kv[0])))
    return ordered[0][0], float(ordered[0][1])


def evaluate_verdict_band(
    prob_yes: float,
    low_threshold: float = VERDICT_LOW_BAND,
    high_threshold: float = VERDICT_HIGH_BAND,
) -> Tuple[str, bool, float]:
    p_yes = min(1.0, max(0.0, float(prob_yes)))
    p_no = 1.0 - p_yes
    if p_yes >= high_threshold:
        return "yes", False, p_yes
    if p_yes <= low_threshold:
        return "no", False, p_no
    predicted = "yes" if p_yes >= 0.5 else "no"
    return predicted, True, max(p_yes, p_no)


def shift_binary_log_odds(prob_yes: float, threshold_tau: float) -> float:
    p = min(1.0 - 1e-6, max(1e-6, float(prob_yes)))
    tau = min(1.0 - 1e-6, max(1e-6, float(threshold_tau)))
    logit_p = math.log(p / (1.0 - p))
    logit_tau = math.log(tau / (1.0 - tau))
    shifted = logit_p - logit_tau
    return 1.0 / (1.0 + math.exp(-shifted))


def apply_temperature_scaling(
    probabilities: Dict[str, float],
    temperature: float,
) -> Dict[str, float]:
    temp = max(0.05, min(10.0, float(temperature)))
    if abs(temp - 1.0) < 1e-6 or not probabilities:
        return dict(probabilities)
    logits = {k: math.log(max(EPS, v)) / temp for k, v in probabilities.items()}
    max_logit = max(logits.values())
    exps = {k: math.exp(val - max_logit) for k, val in logits.items()}
    denom = sum(exps.values()) or 1.0
    return {k: exps[k] / denom for k in probabilities.keys()}


def fit_temperature_scaling(
    distributions: Sequence[Dict[str, float]],
    gold_labels: Sequence[str],
) -> float:
    if not distributions or len(distributions) != len(gold_labels):
        return 1.0

    def nll(temp: float) -> float:
        loss = 0.0
        count = 0
        for dist, gold in zip(distributions, gold_labels):
            if gold not in dist:
                continue
            scaled = apply_temperature_scaling(dist, temp)
            p_gold = max(EPS, scaled.get(gold, EPS))
            loss -= math.log(p_gold)
            count += 1
        return loss / max(1, count)

    candidates = [round(0.2 + 0.05 * i, 4) for i in range(96)]
    best_t = min(candidates, key=nll)
    low = max(0.05, best_t - 0.05)
    high = min(5.0, best_t + 0.05)
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    for _ in range(18):
        c1 = high - (high - low) / phi
        c2 = low + (high - low) / phi
        if nll(c1) < nll(c2):
            high = c2
        else:
            low = c1
    return round((low + high) / 2.0, 4)


def debias_option_order(
    forward_probs: Dict[str, float],
    reverse_probs: Optional[Dict[str, float]] = None,
) -> Tuple[Dict[str, float], float]:
    if not reverse_probs or set(forward_probs.keys()) != set(reverse_probs.keys()):
        return dict(forward_probs), 0.0

    labels = sorted(forward_probs.keys())
    tvd_gap = 0.5 * sum(abs(forward_probs[k] - reverse_probs[k]) for k in labels)
    geo = {
        k: math.sqrt(max(EPS, forward_probs[k]) * max(EPS, reverse_probs[k]))
        for k in labels
    }
    total = sum(geo.values()) or 1.0
    debiased = {k: geo[k] / total for k in labels}
    return debiased, round(tvd_gap, 6)


def ordinal_expected_value(probabilities: Dict[str, float], rubric_levels: int) -> float:
    ev = 0.0
    for level in range(rubric_levels):
        key = str(level)
        ev += level * float(probabilities.get(key, 0.0))
    return round(ev, 6)


def normalized_mae(predicted_value: float, gold_level: int, rubric_levels: int) -> float:
    span = max(1, rubric_levels - 1)
    return min(1.0, max(0.0, abs(float(predicted_value) - float(gold_level)) / span))


def uniform_chance_nmae(gold_level: int, rubric_levels: int) -> float:
    span = max(1, rubric_levels - 1)
    total = sum(abs(level - gold_level) / span for level in range(rubric_levels))
    return total / max(1, rubric_levels)


def chance_corrected_verdict(accuracy: float) -> float:
    return max(0.0, min(100.0, 100.0 * (float(accuracy) - 0.5) / 0.5))


def chance_corrected_choice(accuracy: float, option_counts: Sequence[int]) -> float:
    if not option_counts:
        return 0.0
    mean_chance = sum(1.0 / max(2, k) for k in option_counts) / len(option_counts)
    if mean_chance >= 1.0:
        return 0.0
    return max(0.0, min(100.0, 100.0 * (float(accuracy) - mean_chance) / (1.0 - mean_chance)))


def chance_corrected_rubric(
    item_nmaes: Sequence[float],
    gold_levels: Sequence[int],
    rubric_levels_list: Sequence[int],
) -> float:
    if not item_nmaes or len(item_nmaes) != len(gold_levels):
        return 0.0
    mean_nmae = sum(item_nmaes) / len(item_nmaes)
    chance_values = [
        uniform_chance_nmae(g, k)
        for g, k in zip(gold_levels, rubric_levels_list)
    ]
    mean_chance = sum(chance_values) / max(1, len(chance_values))
    if mean_chance <= EPS:
        return 0.0
    return max(0.0, min(100.0, 100.0 * (1.0 - (mean_nmae / mean_chance))))


def compute_conformal_set(
    probabilities: Dict[str, float],
    alpha: float = 0.10,
    nonconformity_quantile: Optional[float] = None,
) -> ConformalPredictionSet:
    clamped_alpha = min(0.50, max(0.01, float(alpha)))
    target = 1.0 - clamped_alpha
    if nonconformity_quantile is not None:
        threshold = min(0.999, max(0.50, 1.0 - float(nonconformity_quantile)))
    else:
        threshold = target

    ordered = sorted(probabilities.items(), key=lambda kv: (-kv[1], str(kv[0])))
    included: List[str] = []
    cumulative = 0.0
    for label, prob in ordered:
        included.append(label)
        cumulative += float(prob)
        if cumulative >= threshold:
            break

    return ConformalPredictionSet(
        alpha=round(clamped_alpha, 4),
        coverage_target=round(target, 4),
        included_labels=included,
        cumulative_mass=round(min(1.0, cumulative), 6),
        set_size=len(included),
        is_singleton=len(included) == 1,
    )


def decompose_uncertainty(
    member_distributions: Sequence[Dict[str, float]],
) -> UncertaintyDecomposition:
    if not member_distributions:
        return UncertaintyDecomposition(
            total_entropy=0.0,
            aleatoric_entropy=0.0,
            epistemic_divergence=0.0,
            normalized_confidence=0.0,
        )

    labels = sorted(member_distributions[0].keys())
    k_count = max(2, len(labels))
    max_entropy = math.log(k_count)

    pooled = {
        k: sum(float(d.get(k, 0.0)) for d in member_distributions) / len(member_distributions)
        for k in labels
    }

    def shannon(dist: Dict[str, float]) -> float:
        return -sum(
            p * math.log(max(EPS, p))
            for p in dist.values()
            if p > 0.0
        )

    total_h = shannon(pooled)
    aleatoric_h = sum(shannon(d) for d in member_distributions) / len(member_distributions)
    epistemic_mi = max(0.0, total_h - aleatoric_h)
    norm_conf = max(0.0, min(1.0, 1.0 - (total_h / max_entropy)))

    return UncertaintyDecomposition(
        total_entropy=round(total_h, 6),
        aleatoric_entropy=round(aleatoric_h, 6),
        epistemic_divergence=round(epistemic_mi, 6),
        normalized_confidence=round(norm_conf, 6),
    )
