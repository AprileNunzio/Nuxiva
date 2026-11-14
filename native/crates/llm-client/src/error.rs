#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ClientError {
    Url,
    Build,
    Transport,
    Timeout,
    TooLarge,
    Json,
}

impl std::fmt::Display for ClientError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let code = match self {
            Self::Url => "llm.client.url_invalid",
            Self::Build => "llm.client.build_failed",
            Self::Transport => "llm.client.transport",
            Self::Timeout => "llm.client.timeout",
            Self::TooLarge => "llm.client.too_large",
            Self::Json => "llm.client.json_invalid",
        };
        f.write_str(code)
    }
}

impl std::error::Error for ClientError {}
