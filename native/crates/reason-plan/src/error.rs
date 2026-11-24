use std::fmt;

#[derive(Debug, PartialEq, Eq)]
pub enum PlanError {
    Invalid(&'static str),
    TooManySteps,
    DuplicateStep(String),
    UnknownStep(String),
    Cycle,
    UnknownCapability(String),
    RoleDenied(String),
    MissingInput { step: String, input: String },
    UnknownInput { step: String, input: String },
    TypeMismatch { step: String, input: String },
    UnknownEntity { step: String, role: String },
    EffectNotRequested { step: String },
    ExternalTarget { step: String },
}

pub type PlanResult<T> = Result<T, PlanError>;

impl fmt::Display for PlanError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invalid(what) => write!(f, "plan.invalid.{what}"),
            Self::TooManySteps => f.write_str("plan.too_many_steps"),
            Self::DuplicateStep(id) => write!(f, "plan.duplicate_step.{id}"),
            Self::UnknownStep(id) => write!(f, "plan.unknown_step.{id}"),
            Self::Cycle => f.write_str("plan.cycle"),
            Self::UnknownCapability(id) => write!(f, "plan.unknown_capability.{id}"),
            Self::RoleDenied(id) => write!(f, "plan.role_denied.{id}"),
            Self::MissingInput { step, input } => write!(f, "plan.missing_input.{step}.{input}"),
            Self::UnknownInput { step, input } => write!(f, "plan.unknown_input.{step}.{input}"),
            Self::TypeMismatch { step, input } => write!(f, "plan.type_mismatch.{step}.{input}"),
            Self::UnknownEntity { step, role } => write!(f, "plan.unknown_entity.{step}.{role}"),
            Self::EffectNotRequested { step } => write!(f, "plan.effect_not_requested.{step}"),
            Self::ExternalTarget { step } => write!(f, "plan.external_target.{step}"),
        }
    }
}

impl std::error::Error for PlanError {}
