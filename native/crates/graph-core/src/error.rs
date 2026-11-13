#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GraphError {
    Settings,
    Path,
    TooLarge,
    Source,
    Capacity,
    Unknown,
}

impl GraphError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Settings => "graph.settings.invalid",
            Self::Path => "graph.path.invalid",
            Self::TooLarge => "graph.too_large",
            Self::Source => "graph.source",
            Self::Capacity => "graph.capacity",
            Self::Unknown => "graph.unknown",
        }
    }
}

impl std::fmt::Display for GraphError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for GraphError {}

pub type GraphResult<T> = Result<T, GraphError>;
