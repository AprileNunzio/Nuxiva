use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StudioError {
    Invalid(&'static str),
    Insecure,
    Unsupported(&'static str),
    Auth,
    Busy,
    Rejected(u16),
    Upstream(u16),
    Transport,
    Timeout,
    TooLarge,
    Malformed(&'static str),
}

pub type StudioResult<T> = Result<T, StudioError>;

impl fmt::Display for StudioError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invalid(what) => write!(f, "studio.error.invalid.{what}"),
            Self::Insecure => f.write_str("studio.error.insecure_endpoint"),
            Self::Unsupported(what) => write!(f, "studio.error.unsupported.{what}"),
            Self::Auth => f.write_str("studio.error.auth"),
            Self::Busy => f.write_str("studio.error.busy"),
            Self::Rejected(code) => write!(f, "studio.error.rejected.{code}"),
            Self::Upstream(code) => write!(f, "studio.error.upstream.{code}"),
            Self::Transport => f.write_str("studio.error.transport"),
            Self::Timeout => f.write_str("studio.error.timeout"),
            Self::TooLarge => f.write_str("studio.error.too_large"),
            Self::Malformed(what) => write!(f, "studio.error.malformed.{what}"),
        }
    }
}

impl std::error::Error for StudioError {}

impl From<serde_json::Error> for StudioError {
    fn from(_: serde_json::Error) -> Self {
        Self::Malformed("json")
    }
}
