use serde::{Deserialize, Serialize};

use crate::error::McpError;

pub const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ErrorKind {
    Unavailable,
    Timeout,
    Denied,
    ConsentRequired,
    RateLimited,
    Invalid,
    Remote,
    Internal,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ToolError {
    pub schema_version: u32,
    pub kind: ErrorKind,
    pub code: String,
    pub tool: String,
    pub retryable: bool,
}

#[must_use]
pub fn kind_of(error: McpError) -> ErrorKind {
    match error {
        McpError::Timeout => ErrorKind::Timeout,
        McpError::Closed | McpError::Busy | McpError::Io | McpError::NotCallable => {
            ErrorKind::Unavailable
        }
        McpError::Remote => ErrorKind::Remote,
        McpError::NotPermitted
        | McpError::ConsentDenied
        | McpError::NetworkDenied
        | McpError::SecretMissing
        | McpError::SignatureInvalid => ErrorKind::Denied,
        McpError::ConsentRequired => ErrorKind::ConsentRequired,
        McpError::RateLimited => ErrorKind::RateLimited,
        McpError::InvalidArguments
        | McpError::InvalidOutput
        | McpError::InvalidTool
        | McpError::UnknownTool
        | McpError::InvalidName
        | McpError::InvalidSettings => ErrorKind::Invalid,
        _ => ErrorKind::Internal,
    }
}

impl ToolError {
    #[must_use]
    pub fn new(error: McpError, tool: &str) -> Self {
        let kind = kind_of(error);
        Self {
            schema_version: SCHEMA_VERSION,
            kind,
            code: error.code().to_owned(),
            tool: tool.to_owned(),
            retryable: matches!(
                kind,
                ErrorKind::Unavailable | ErrorKind::Timeout | ErrorKind::RateLimited
            ),
        }
    }

    #[must_use]
    pub fn from_code(code: &str, tool: &str) -> Self {
        McpError::from_code(code).map_or_else(
            || Self {
                schema_version: SCHEMA_VERSION,
                kind: ErrorKind::Internal,
                code: code.to_owned(),
                tool: tool.to_owned(),
                retryable: false,
            },
            |error| Self::new(error, tool),
        )
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ErrorPayload {
    pub schema_version: u32,
    pub component: String,
    pub code: String,
    pub context: String,
    pub hash: String,
    pub at_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ToolsChanged {
    pub schema_version: u32,
    pub version: u64,
}
