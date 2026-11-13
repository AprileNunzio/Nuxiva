use nuxiva_context_core::ContextError;
use nuxiva_swarm_core::SwarmError;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PerceptError {
    Invalid,
    TooLarge,
    Clock,
    Context(ContextError),
    Swarm(SwarmError),
}

pub type PerceptResult<T> = Result<T, PerceptError>;

impl PerceptError {
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::Invalid => "percept.invalid",
            Self::TooLarge => "percept.too_large",
            Self::Clock => "percept.clock",
            Self::Context(_) => "percept.context",
            Self::Swarm(_) => "percept.swarm",
        }
    }
}

impl std::fmt::Display for PerceptError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for PerceptError {}

impl From<ContextError> for PerceptError {
    fn from(value: ContextError) -> Self {
        Self::Context(value)
    }
}

impl From<SwarmError> for PerceptError {
    fn from(value: SwarmError) -> Self {
        Self::Swarm(value)
    }
}
