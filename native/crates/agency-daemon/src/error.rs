use agency_domain::DomainError;
use agency_foresight::ForesightError;
use agency_ledger::LedgerError;
use agency_planner::PlanError;
use agency_scheduler::SettingsError;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AgencyError {
    #[error("config: {0}")]
    Config(&'static str),
    #[error(transparent)]
    Domain(#[from] DomainError),
    #[error(transparent)]
    Plan(#[from] PlanError),
    #[error(transparent)]
    Ledger(#[from] LedgerError),
    #[error(transparent)]
    Settings(#[from] SettingsError),
    #[error(transparent)]
    Foresight(#[from] ForesightError),
    #[error("sealed state cannot be opened")]
    Sealed,
    #[error("another simulation batch is running")]
    Busy,
    #[error("project not found")]
    NotFound,
    #[error("project already exists")]
    Exists,
    #[error("project limit reached")]
    TooMany,
    #[error("workspace escapes the shared folder")]
    Escape,
    #[error("request rejected: {0}")]
    BadRequest(String),
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
    #[error("json: {0}")]
    Json(#[from] serde_json::Error),
}

impl AgencyError {
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::Config(_) => "config",
            Self::NotFound | Self::Foresight(ForesightError::AgentNotFound) => "not_found",
            Self::Domain(_) | Self::Foresight(_) => "invalid",
            Self::Plan(_) => "plan",
            Self::Ledger(_) => "ledger",
            Self::Settings(_) => "settings",
            Self::Sealed => "sealed",
            Self::Busy => "busy",
            Self::Exists => "exists",
            Self::TooMany => "too_many",
            Self::Escape => "escape",
            Self::BadRequest(_) => "bad_request",
            Self::Io(_) | Self::Json(_) => "internal",
        }
    }

    #[must_use]
    pub fn public_message(&self) -> String {
        match self {
            Self::Io(_) | Self::Json(_) | Self::Ledger(_) | Self::Sealed => {
                "internal error".to_owned()
            }
            other => other.to_string(),
        }
    }
}
