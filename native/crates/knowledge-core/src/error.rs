#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum KnowledgeError {
    Invalid,
    TooLarge,
    Settings,
    Seal,
    Forbidden,
    NotFound,
    Capacity,
    Corrupt,
    Io,
    Confirm,
}

impl KnowledgeError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Invalid => "knowledge.invalid",
            Self::TooLarge => "knowledge.too_large",
            Self::Settings => "knowledge.settings.invalid",
            Self::Seal => "knowledge.seal",
            Self::Forbidden => "knowledge.forbidden",
            Self::NotFound => "knowledge.not_found",
            Self::Capacity => "knowledge.capacity",
            Self::Corrupt => "knowledge.corrupt",
            Self::Io => "knowledge.io",
            Self::Confirm => "knowledge.confirm",
        }
    }
}

impl std::fmt::Display for KnowledgeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for KnowledgeError {}

pub type KnowledgeResult<T> = Result<T, KnowledgeError>;
