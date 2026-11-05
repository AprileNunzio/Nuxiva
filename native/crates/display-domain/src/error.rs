#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DomainError {
    SectionKey,
}

impl DomainError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::SectionKey => "display.section.invalid",
        }
    }
}

impl std::fmt::Display for DomainError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for DomainError {}
