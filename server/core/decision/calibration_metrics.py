from typing import Dict, List, Optional, Sequence, Tuple
from server.core.decision.contracts import CalibrationSummary
from server.core.decision.scoring_math import deterministic_argmax


def multiclass_brier_score(
    probabilities: Dict[str, float],
    gold_label: str,
) -> float:
    if not probabilities:
        return 2.0
    total = 0.0
    for label, prob in probabilities.items():
        target = 1.0 if label == gold_label else 0.0
        diff = float(prob) - target
        total += diff * diff
    return round(total, 6)


def binary_brier_two_class(prob_yes: float, gold_is_yes: bool) -> float:
    target = 1.0 if gold_is_yes else 0.0
    diff = float(prob_yes) - target
    return round(2.0 * diff * diff, 6)


def total_variation_distance(
    predicted_probs: Dict[str, float],
    reference_probs: Dict[str, float],
) -> float:
    keys = set(predicted_probs.keys()).union(reference_probs.keys())
    if not keys:
        return 1.0
    tvd = 0.5 * sum(
        abs(float(predicted_probs.get(k, 0.0)) - float(reference_probs.get(k, 0.0)))
        for k in keys
    )
    return round(min(1.0, max(0.0, tvd)), 6)


def ranked_probability_score(
    probabilities: Dict[str, float],
    gold_level: int,
    rubric_levels: int,
    gold_distribution: Optional[Dict[str, float]] = None,
) -> float:
    if rubric_levels <= 1:
        return 0.0
    cum_pred = 0.0
    cum_gold = 0.0
    sq_sum = 0.0
    for level in range(rubric_levels - 1):
        key = str(level)
        cum_pred += float(probabilities.get(key, 0.0))
        if gold_distribution is not None:
            cum_gold += float(gold_distribution.get(key, 0.0))
        else:
            cum_gold += 1.0 if level >= gold_level else 0.0
        diff = cum_pred - cum_gold
        sq_sum += diff * diff
    return round(sq_sum / float(rubric_levels - 1), 6)


def expected_calibration_error_10bin(
    confidences: Sequence[float],
    correctness: Sequence[bool],
    num_bins: int = 10,
) -> float:
    n_items = len(confidences)
    if n_items == 0 or n_items != len(correctness):
        return 0.5

    bin_totals = [0] * num_bins
    bin_conf_sums = [0.0] * num_bins
    bin_acc_sums = [0.0] * num_bins

    for conf, is_correct in zip(confidences, correctness):
        c_val = min(1.0, max(0.0, float(conf)))
        idx = min(num_bins - 1, int(c_val * num_bins))
        bin_totals[idx] += 1
        bin_conf_sums[idx] += c_val
        bin_acc_sums[idx] += 1.0 if is_correct else 0.0

    ece = 0.0
    for idx in range(num_bins):
        count = bin_totals[idx]
        if count > 0:
            avg_conf = bin_conf_sums[idx] / count
            avg_acc = bin_acc_sums[idx] / count
            ece += (count / n_items) * abs(avg_acc - avg_conf)

    return round(min(1.0, max(0.0, ece)), 6)


def paraphrase_consistency_metrics(
    group_ids: Sequence[Optional[str]],
    predicted_labels: Sequence[str],
    gold_labels: Sequence[Optional[str]],
    valid_flags: Sequence[bool],
) -> Tuple[float, float]:
    groups: Dict[str, List[Tuple[str, Optional[str], bool]]] = {}
    for gid, pred, gold, valid in zip(group_ids, predicted_labels, gold_labels, valid_flags):
        if not gid:
            continue
        groups.setdefault(gid, []).append((pred, gold, valid))

    multi_groups = [items for items in groups.values() if len(items) >= 2]
    if not multi_groups:
        return 1.0, 1.0

    agree_count = 0
    both_correct_count = 0
    evaluated_groups = 0

    for items in multi_groups:
        if not all(v for _, _, v in items):
            evaluated_groups += 1
            continue
        evaluated_groups += 1
        labels_set = {pred for pred, _, _ in items}
        if len(labels_set) == 1:
            agree_count += 1
            if all(gold is not None and pred == gold for pred, gold, _ in items):
                both_correct_count += 1

    denom = max(1, evaluated_groups)
    return round(agree_count / denom, 6), round(both_correct_count / denom, 6)


def summarize_calibration(
    distributions: Sequence[Dict[str, float]],
    gold_labels: Sequence[str],
    ordinal_rps_values: Optional[Sequence[float]] = None,
    tvd_values: Optional[Sequence[float]] = None,
    paraphrase_agreement: float = 1.0,
    paraphrase_both_correct: float = 1.0,
    option_order_gaps: Optional[Sequence[float]] = None,
    has_calibrated_probabilities: bool = True,
) -> CalibrationSummary:
    if not has_calibrated_probabilities or not distributions or len(distributions) != len(gold_labels):
        return CalibrationSummary(
            brier_score=2.0,
            ece_10bin=0.5,
            tvd_mean=1.0,
            rps_mean=1.0,
            paraphrase_agreement=round(paraphrase_agreement, 4),
            paraphrase_both_correct=round(paraphrase_both_correct, 4),
            option_order_consistency=0.0,
            pooled_calibration_score=0.0,
        )

    briers: List[float] = []
    confidences: List[float] = []
    correctness: List[bool] = []

    for dist, gold in zip(distributions, gold_labels):
        briers.append(multiclass_brier_score(dist, gold))
        top_label, top_conf = deterministic_argmax(dist)
        confidences.append(top_conf)
        correctness.append(top_label == gold)

    mean_brier = sum(briers) / len(briers)
    ece = expected_calibration_error_10bin(confidences, correctness)
    tvd_mean = (sum(tvd_values) / len(tvd_values)) if tvd_values else (0.5 * mean_brier)
    rps_mean = (sum(ordinal_rps_values) / len(ordinal_rps_values)) if ordinal_rps_values else (0.5 * mean_brier)

    if option_order_gaps:
        mean_gap = sum(option_order_gaps) / len(option_order_gaps)
        order_consistency = max(0.0, min(1.0, 1.0 - mean_gap))
    else:
        order_consistency = 1.0

    ece_score = max(0.0, min(100.0, 100.0 * (1.0 - (ece / 0.5))))
    brier_score_100 = max(0.0, min(100.0, 100.0 * (1.0 - (mean_brier / 1.0))))
    rps_score_100 = max(0.0, min(100.0, 100.0 * (1.0 - (rps_mean / 0.5))))
    order_score_100 = 100.0 * order_consistency

    pooled = (
        0.50 * ece_score
        + 0.25 * brier_score_100
        + 0.15 * rps_score_100
        + 0.10 * order_score_100
    )

    return CalibrationSummary(
        brier_score=round(mean_brier, 4),
        ece_10bin=round(ece, 4),
        tvd_mean=round(tvd_mean, 4),
        rps_mean=round(rps_mean, 4),
        paraphrase_agreement=round(paraphrase_agreement, 4),
        paraphrase_both_correct=round(paraphrase_both_correct, 4),
        option_order_consistency=round(order_consistency, 4),
        pooled_calibration_score=round(max(0.0, min(100.0, pooled)), 2),
    )
