from typing import Optional
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
