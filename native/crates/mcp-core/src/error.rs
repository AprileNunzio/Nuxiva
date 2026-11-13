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
    ChainBroken,
    SignatureInvalid,
    CatalogExpired,
    NetworkDenied,
    ConsentRequired,
    ConsentDenied,
    RateLimited,
    NotPermitted,
    SecretMissing,
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
            Self::ChainBroken => "mcp.audit.chain_broken",
            Self::SignatureInvalid => "mcp.catalog.signature_invalid",
            Self::CatalogExpired => "mcp.catalog.expired",
            Self::NetworkDenied => "mcp.network.denied",
            Self::ConsentRequired => "mcp.consent.required",
            Self::ConsentDenied => "mcp.consent.denied",
            Self::RateLimited => "mcp.rate_limited",
            Self::NotPermitted => "mcp.not_permitted",
            Self::SecretMissing => "mcp.secret.missing",
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
