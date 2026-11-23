#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error, uniffi::Error)]
pub enum MobileError {
    #[error("{code}")]
    Rejected { code: String },
}

impl MobileError {
    #[must_use]
    pub fn code(code: &str) -> Self {
        Self::Rejected {
            code: code.to_owned(),
        }
    }
}

impl From<nuxiva_node_core::NodeError> for MobileError {
    fn from(error: nuxiva_node_core::NodeError) -> Self {
        Self::code(error.code())
    }
}

pub type MobileResult<T> = Result<T, MobileError>;
