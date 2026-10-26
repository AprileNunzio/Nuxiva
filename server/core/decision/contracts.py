import hashlib
import json
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator
from server.shared.errors.domain_errors import NuxivaBaseException

BANNED_STATE_KEYS = frozenset({"expected", "label", "ground_truth", "answer_key", "gold", "target_label"})


class DecisionDomainException(NuxivaBaseException):
    def __init__(self, message: str, code: str = "SANDBOX_VIOLATION", details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message=message, code=code, details=details)


class DecisionPrimitive(str, Enum):
    VERDICT = "verdict"
    CHOICE = "choice"
    RUBRIC = "rubric"


class TaskTier(str, Enum):
    EASY = "easy"
    STANDARD = "standard"
    JUDGE = "judge"
    HARD = "hard"


class TaskSplit(str, Enum):
    OPEN = "open"
    SEALED = "sealed"


class TaskFamily(str, Enum):
    INTENT_ROUTING = "intent_routing"
    TOOL_CALL_GUARDRAIL = "tool_call_guardrail"
    STATE_TRACKING = "state_tracking"
    LEAD_QUALIFICATION = "lead_qualification"
    SAFETY_MODERATION = "safety_moderation"
    RUBRIC_EVALUATION = "rubric_evaluation"


class CanonicalDecisionTask(BaseModel):
    task_id: str = Field(..., min_length=1, max_length=120)
    primitive: DecisionPrimitive
    tier: TaskTier = TaskTier.STANDARD
    split: TaskSplit = TaskSplit.OPEN
    family: TaskFamily = TaskFamily.INTENT_ROUTING
    group_id: Optional[str] = None
    state: Dict[str, Any]
    proposition: Optional[str] = None
    options: Optional[List[str]] = None
    rubric_levels: int = Field(default=5, ge=2, le=20)
    gold_label: Optional[str] = None
    gold_score: Optional[int] = None
    gold_distribution: Optional[Dict[str, float]] = None

    @field_validator("state")
    @classmethod
    def validate_anti_leakage(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        leaked = BANNED_STATE_KEYS.intersection({str(k).lower() for k in value.keys()})
        if leaked:
            raise DecisionDomainException(
                message="Anti-leakage violation in canonical decision task state",
                details={"leaked_keys": sorted(leaked)},
            )
        return value

    def canonical_payload(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "primitive": self.primitive.value,
            "tier": self.tier.value,
            "split": self.split.value,
            "family": self.family.value,
            "group_id": self.group_id,
            "state": self.state,
            "proposition": self.proposition,
            "options": self.options,
            "rubric_levels": self.rubric_levels,
        }


def compute_dataset_hash(tasks: List[CanonicalDecisionTask]) -> str:
    canonical_lines = sorted(
        json.dumps(task.canonical_payload(), sort_keys=True, separators=(",", ":"))
        for task in tasks
    )
    digest = hashlib.sha256("\n".join(canonical_lines).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


class DistributionValidation(BaseModel):
    valid: bool
    strict_valid: bool
    renormalized: bool
    probabilities: Dict[str, float]
    raw_sum: float
    error_reason: Optional[str] = None


class ConformalPredictionSet(BaseModel):
    alpha: float
    coverage_target: float
    included_labels: List[str]
    cumulative_mass: float
    set_size: int
    is_singleton: bool


class UncertaintyDecomposition(BaseModel):
    total_entropy: float
    aleatoric_entropy: float
    epistemic_divergence: float
    normalized_confidence: float


class TypedDecisionOutput(BaseModel):
    primitive: DecisionPrimitive
    valid: bool
    strict_valid: bool
    renormalized: bool
    predicted_label: str
    abstained: bool = False
    expected_value: float = 0.0
    confidence: float = 0.0
    probabilities: Dict[str, float]
    calibrated_temperature: float = 1.0
    option_order_gap: float = 0.0
    conformal_set: ConformalPredictionSet
    uncertainty: UncertaintyDecomposition
    latency_ms: float = 0.0
    cost_usd: float = 0.0


class CalibrationSummary(BaseModel):
    brier_score: float
    ece_10bin: float
    tvd_mean: float
    rps_mean: float
    paraphrase_agreement: float
    paraphrase_both_correct: float
    option_order_consistency: float
    pooled_calibration_score: float


class DecisionAxisScores(BaseModel):
    intelligence: float
    calibration: float
    speed: float
    cost: float
    security_homeostasis: float


class BootstrapInterval(BaseModel):
    mean: float
    ci_lower_95: float
    ci_upper_95: float
    std_error: float
    samples: int


class CompositeEvaluation(BaseModel):
    preset: Literal["A_BALANCED", "B_QUALITY", "C_PRODUCTION", "NUXIVA_5AXIS"]
    axes: DecisionAxisScores
    capability_score: float
    within_official_caps: bool
    raw_harmonic_mean: float
    floor_gate_multiplier: float
    overfit_penalty_multiplier: float
    open_sealed_gap: float
    composite_score: float
    bootstrap_ci: Optional[BootstrapInterval] = None


class CascadeOutcome(BaseModel):
    selected_tier: Literal["system1_fast", "system2_deep"]
    escalated: bool
    escalation_threshold: float
    fast_confidence: float
    final_decision: TypedDecisionOutput
    estimated_cost_saved_ratio: float


class CommitteeMemberVote(BaseModel):
    member_id: str
    calibration_score: float
    intelligence_score: float
    weight: float
    probabilities: Dict[str, float]


class CommitteeOutcome(BaseModel):
    consensus_label: str
    consensus_confidence: float
    pooled_probabilities: Dict[str, float]
    epistemic_disagreement: float
    member_votes: List[CommitteeMemberVote]
    conformal_set: ConformalPredictionSet
