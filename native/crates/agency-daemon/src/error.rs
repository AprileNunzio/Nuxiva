use agency_domain::DomainError;
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
            Self::Domain(_) => "invalid",
            Self::Plan(_) => "plan",
            Self::Ledger(_) => "ledger",
            Self::Settings(_) => "settings",
            Self::NotFound => "not_found",
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
            Self::Io(_) | Self::Json(_) | Self::Ledger(_) => "internal error".to_owned(),
            other => other.to_string(),
        }
    }
}
