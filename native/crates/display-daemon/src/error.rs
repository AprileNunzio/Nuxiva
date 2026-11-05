use nuxiva_display_scheduler::SchedulerError;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum DisplayError {
    #[error("config: {0}")]
    Config(&'static str),
    #[error("scheduler: {0}")]
    Scheduler(#[from] SchedulerError),
    #[error("patch: {0}")]
    Patch(&'static str),
    #[error("request rejected: {0}")]
    BadRequest(String),
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
    #[error("json: {0}")]
    Json(#[from] serde_json::Error),
}

impl DisplayError {
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::Config(_) => "display.config",
            Self::Scheduler(e) => e.code(),
            Self::Patch(code) => code,
            Self::BadRequest(_) => "display.bad_request",
            Self::Io(_) | Self::Json(_) => "display.internal",
        }
    }
}
