from typing import Callable, Dict, List, Sequence, Tuple
from server.core.decision.contracts import (
    CascadeOutcome,
    CommitteeMemberVote,
    CommitteeOutcome,
    TypedDecisionOutput,
)
from server.core.decision.scoring_math import (
    compute_conformal_set,
    decompose_uncertainty,
    deterministic_argmax,
    validate_distribution,
)


class ConfidenceCascadeEngine:
    def __init__(self, default_threshold: float = 0.82) -> None:
        self._threshold = min(0.99, max(0.50, float(default_threshold)))

    @property
    def threshold(self) -> float:
        return self._threshold

    def set_threshold(self, tau: float) -> float:
        self._threshold = round(min(0.99, max(0.50, float(tau))), 4)
        return self._threshold

    def should_escalate(
        self,
        fast_output: TypedDecisionOutput,
        require_singleton_conformal: bool = False,
    ) -> bool:
        if not fast_output.valid or fast_output.abstained:
            return True
        if fast_output.confidence < self._threshold:
            return True
        if require_singleton_conformal and not fast_output.conformal_set.is_singleton:
            return True
        return False

    def execute_cascade(
        self,
        fast_output: TypedDecisionOutput,
        deep_provider: Callable[[], TypedDecisionOutput],
        require_singleton_conformal: bool = False,
        deep_to_fast_cost_ratio: float = 8.0,
    ) -> CascadeOutcome:
        escalate = self.should_escalate(fast_output, require_singleton_conformal)
        if not escalate:
            saved_ratio = max(0.0, 1.0 - (1.0 / max(1.0, float(deep_to_fast_cost_ratio))))
            return CascadeOutcome(
                selected_tier="system1_fast",
                escalated=False,
                escalation_threshold=self._threshold,
                fast_confidence=round(fast_output.confidence, 4),
                final_decision=fast_output,
                estimated_cost_saved_ratio=round(saved_ratio, 4),
            )

        deep_output = deep_provider()
        return CascadeOutcome(
            selected_tier="system2_deep",
            escalated=True,
            escalation_threshold=self._threshold,
            fast_confidence=round(fast_output.confidence, 4),
            final_decision=deep_output,
            estimated_cost_saved_ratio=0.0,
        )

    def fit_optimal_threshold(
        self,
        fast_confidences: Sequence[float],
        fast_predictions: Sequence[str],
        deep_predictions: Sequence[str],
        gold_labels: Sequence[str],
        target_accuracy_retention: float = 0.99,
    ) -> Dict[str, float]:
        n_total = len(gold_labels)
        if (
            n_total == 0
            or len(fast_confidences) != n_total
            or len(fast_predictions) != n_total
            or len(deep_predictions) != n_total
        ):
            return {
                "optimal_threshold": self._threshold,
                "escalation_rate": 0.0,
                "cascade_accuracy": 0.0,
                "deep_accuracy": 0.0,
            }

        deep_correct = sum(1 for d, g in zip(deep_predictions, gold_labels) if d == g)
        deep_acc = deep_correct / n_total
        required_acc = deep_acc * min(1.0, max(0.80, float(target_accuracy_retention)))

        best_tau = 0.95
        best_escalation_rate = 1.0
        best_acc = deep_acc

        for step in range(50, 100):
            tau = step / 100.0
            correct = 0
            escalated = 0
            for conf, f_pred, d_pred, gold in zip(
                fast_confidences, fast_predictions, deep_predictions, gold_labels
            ):
                if float(conf) < tau:
                    escalated += 1
                    chosen = d_pred
                else:
                    chosen = f_pred
                if chosen == gold:
                    correct += 1

            acc = correct / n_total
            esc_rate = escalated / n_total
            if acc >= required_acc - 1e-6 and esc_rate <= best_escalation_rate:
                best_tau = tau
                best_escalation_rate = esc_rate
                best_acc = acc

        self._threshold = round(best_tau, 4)
        return {
            "optimal_threshold": self._threshold,
            "escalation_rate": round(best_escalation_rate, 4),
            "cascade_accuracy": round(best_acc, 4),
            "deep_accuracy": round(deep_acc, 4),
        }


class CalibrationWeightedCommittee:
    def __init__(self, competence_exponent: float = 0.5) -> None:
        self._competence_exponent = max(0.0, min(2.0, float(competence_exponent)))

    def combine(
        self,
        members: Sequence[Tuple[str, Dict[str, float], float, float]],
        expected_labels: Sequence[str],
        conformal_alpha: float = 0.10,
    ) -> CommitteeOutcome:
        valid_votes: List[CommitteeMemberVote] = []
        raw_weights: List[float] = []

        for member_id, raw_probs, cal_score, int_score in members:
            validation = validate_distribution(raw_probs, expected_labels)
            if not validation.valid:
                continue
            c_norm = max(0.01, min(100.0, float(cal_score))) / 100.0
            i_norm = max(0.01, min(100.0, float(int_score))) / 100.0
            w = c_norm * (i_norm ** self._competence_exponent)
            raw_weights.append(w)
            valid_votes.append(
                CommitteeMemberVote(
                    member_id=str(member_id),
                    calibration_score=round(float(cal_score), 2),
                    intelligence_score=round(float(int_score), 2),
                    weight=w,
                    probabilities=validation.probabilities,
                )
            )

        if not valid_votes:
            uniform_p = 1.0 / max(1, len(expected_labels))
            fallback = {label: round(uniform_p, 6) for label in expected_labels}
            top_label, top_conf = deterministic_argmax(fallback)
            return CommitteeOutcome(
                consensus_label=top_label,
                consensus_confidence=round(top_conf, 4),
                pooled_probabilities=fallback,
                epistemic_disagreement=0.0,
                member_votes=[],
                conformal_set=compute_conformal_set(fallback, alpha=conformal_alpha),
            )

        total_w = sum(raw_weights) or 1.0
        normalized_votes: List[CommitteeMemberVote] = []
        pooled: Dict[str, float] = {label: 0.0 for label in expected_labels}

        for vote in valid_votes:
            norm_w = vote.weight / total_w
            normalized_votes.append(
                CommitteeMemberVote(
                    member_id=vote.member_id,
                    calibration_score=vote.calibration_score,
                    intelligence_score=vote.intelligence_score,
                    weight=round(norm_w, 4),
                    probabilities={k: round(v, 6) for k, v in vote.probabilities.items()},
                )
            )
            for label in expected_labels:
                pooled[label] += norm_w * float(vote.probabilities.get(label, 0.0))

        p_sum = sum(pooled.values()) or 1.0
        pooled = {k: round(v / p_sum, 6) for k, v in pooled.items()}
        top_label, top_conf = deterministic_argmax(pooled)
        uncertainty = decompose_uncertainty([v.probabilities for v in normalized_votes])
        conformal = compute_conformal_set(pooled, alpha=conformal_alpha)

        return CommitteeOutcome(
            consensus_label=top_label,
            consensus_confidence=round(top_conf, 4),
            pooled_probabilities=pooled,
            epistemic_disagreement=uncertainty.epistemic_divergence,
            member_votes=normalized_votes,
            conformal_set=conformal,
        )
