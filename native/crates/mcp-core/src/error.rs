#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum McpError {
    Parse,
    InvalidMessage,
    TooLarge,
    TooDeep,
    UnsupportedVersion,
    InvalidTool,
    InvalidSettings,
    InvalidName,
    Serialize,
    Timeout,
    Closed,
    Remote,
    Busy,
    Io,
    InvalidArguments,
    InvalidOutput,
    NotCallable,
    UnknownTool,
}

impl McpError {
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::Parse => "mcp.parse",
            Self::InvalidMessage => "mcp.message.invalid",
            Self::TooLarge => "mcp.too_large",
            Self::TooDeep => "mcp.too_deep",
            Self::UnsupportedVersion => "mcp.version.unsupported",
            Self::InvalidTool => "mcp.tool.invalid",
            Self::InvalidSettings => "mcp.settings.invalid",
            Self::InvalidName => "mcp.name.invalid",
            Self::Serialize => "mcp.serialize",
            Self::Timeout => "mcp.timeout",
            Self::Closed => "mcp.closed",
            Self::Remote => "mcp.remote",
            Self::Busy => "mcp.busy",
            Self::Io => "mcp.io",
            Self::InvalidArguments => "mcp.arguments.invalid",
            Self::InvalidOutput => "mcp.output.invalid",
            Self::NotCallable => "mcp.tool.not_callable",
            Self::UnknownTool => "mcp.tool.unknown",
        }
    }
}

impl std::fmt::Display for McpError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for McpError {}

pub type McpResult<T> = Result<T, McpError>;
