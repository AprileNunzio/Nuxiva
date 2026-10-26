from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from server.core.decision.contracts import DecisionPrimitive


class TypedDecisionRequest(BaseModel):
    task_id: str = Field(default="", max_length=120)
    primitive: DecisionPrimitive = DecisionPrimitive.CHOICE
    query: str = Field(default="", max_length=1200)
    proposition: str = Field(default="", max_length=600)
    options: List[str] = Field(default_factory=list, max_length=16)
    state: Dict[str, Any] = Field(default_factory=dict)
    forward_probs: Dict[str, float] = Field(default_factory=dict)
    reverse_probs: Optional[Dict[str, float]] = None
    rubric_levels: int = Field(default=5, ge=2, le=12)
    temperature: float = Field(default=0.85, ge=0.05, le=5.0)
    threshold_tau: float = Field(default=0.50, ge=0.05, le=0.95)
    active_model: str = Field(default="", max_length=160)
    provider: str = Field(default="", max_length=64)
    base_url: str = Field(default="", max_length=260)


class CascadeDecisionRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1200)
    options: List[str] = Field(default_factory=list, max_length=16)
    escalation_threshold: Optional[float] = Field(default=None, ge=0.50, le=0.99)
    require_singleton_conformal: bool = False
    active_model: str = Field(default="", max_length=160)
    provider: str = Field(default="", max_length=64)
    base_url: str = Field(default="", max_length=260)
    system1_model: str = Field(default="", max_length=160)
    system2_model: str = Field(default="", max_length=160)


class CommitteeMemberInput(BaseModel):
    member_id: str = Field(..., min_length=1, max_length=80)
    probabilities: Dict[str, float]
    calibration_score: float = Field(default=80.0, ge=0.0, le=100.0)
    intelligence_score: float = Field(default=80.0, ge=0.0, le=100.0)


class CommitteeDecisionRequest(BaseModel):
    expected_labels: List[str] = Field(..., min_length=2, max_length=16)
    members: List[CommitteeMemberInput] = Field(..., min_length=1, max_length=12)
    conformal_alpha: float = Field(default=0.10, ge=0.01, le=0.50)


class BenchmarkSuiteRequest(BaseModel):
    preset: Literal["A_BALANCED", "B_QUALITY", "C_PRODUCTION", "NUXIVA_5AXIS"] = "NUXIVA_5AXIS"
    active_model: str = Field(default="", max_length=160)
    provider: str = Field(default="", max_length=64)
    base_url: str = Field(default="", max_length=260)


class ThresholdTuneRequest(BaseModel):
    threshold: float = Field(..., ge=0.50, le=0.99)
