use std::fmt;

#[derive(Debug, PartialEq, Eq)]
pub enum ForgeError {
    Invalid(&'static str),
    Unknown(String),
    WrongStage(String),
    Quarantined(String),
    ApprovalTooLow,
    TooMany,
    Registry(String),
}

pub type ForgeResult<T> = Result<T, ForgeError>;

impl fmt::Display for ForgeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invalid(what) => write!(f, "forge.invalid.{what}"),
            Self::Unknown(id) => write!(f, "forge.unknown.{id}"),
            Self::WrongStage(id) => write!(f, "forge.wrong_stage.{id}"),
            Self::Quarantined(id) => write!(f, "forge.quarantined.{id}"),
            Self::ApprovalTooLow => f.write_str("forge.approval_too_low"),
            Self::TooMany => f.write_str("forge.too_many"),
            Self::Registry(what) => write!(f, "forge.registry.{what}"),
        }
    }
}

impl std::error::Error for ForgeError {}

impl From<capability_registry::RegistryError> for ForgeError {
    fn from(error: capability_registry::RegistryError) -> Self {
        Self::Registry(error.to_string())
    }
}
