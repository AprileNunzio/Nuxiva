from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class QuadraticSolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column_id: str = Field(
        default="col_algebra_sym",
        min_length=3,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_.-]{2,63}$",
    )
    a: float = Field(ge=-1_000_000.0, le=1_000_000.0)
    b: float = Field(ge=-1_000_000.0, le=1_000_000.0)
    c: float = Field(ge=-1_000_000.0, le=1_000_000.0)
    tier: Optional[str] = Field(
        default=None,
        pattern=r"^(procedural|canonical|invariant)$",
    )


class ConsolidateShortcutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern_signature: str = Field(
        min_length=3,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_.-]{2,63}$",
    )
    a: float = Field(ge=-1_000_000.0, le=1_000_000.0)
    b: float = Field(ge=-1_000_000.0, le=1_000_000.0)
    c: float = Field(ge=-1_000_000.0, le=1_000_000.0)


class ActiveInferenceStepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    joint_id: str = Field(
        min_length=3,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_.-]{2,63}$",
    )
    target_angle_rad: float = Field(ge=-3.14159, le=3.14159)
    feedforward_torque_nm: float = Field(ge=-250.0, le=250.0)
    dt_sec: float = Field(default=0.02, ge=0.001, le=1.0)
    measured_load_kg: float = Field(default=1.5, ge=0.0, le=100.0)
    measured_angle_override: Optional[float] = Field(default=None, ge=-3.14159, le=3.14159)


class EpistemicHypothesisSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9_.-]+$")
    label: str = Field(min_length=2, max_length=128)
    prior_probability: float = Field(ge=0.0, le=1.0)
    predicted_outcome: str = Field(min_length=1, max_length=256)
    action_plan: str = Field(min_length=1, max_length=256)


class InitiateConfrontationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9_.-]+$")
    context_key: str = Field(min_length=3, max_length=128)
    hypotheses: List[EpistemicHypothesisSchema] = Field(min_length=2, max_length=8)


class ResolveConfrontationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9_.-]+$")
    choice_id: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9_.-]+$")
    justification: str = Field(min_length=3, max_length=512)


class SynthesizeFormalismRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9_.-]+$")
    paradigm: str = Field(
        pattern=r"^(calculus|riemann_metric|lie_algebra|symplectic_geometry|discrete_topology)$"
    )
    observations: List[List[float]] = Field(min_length=3, max_length=128)


class FieldbusTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_state: str = Field(
        pattern=r"^(not_ready_to_switch_on|switch_on_disabled|ready_to_switch_on|switched_on|operation_enabled|quick_stop_active|fault_reaction_active|fault)$"
    )
    controlword: int = Field(ge=0, le=65535)
