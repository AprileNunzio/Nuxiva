#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StreamError {
    Pointer,
    Missing,
    NotObject,
    TooManyOps,
    TooDeep,
    Version,
}

impl StreamError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Pointer => "display.patch.pointer",
            Self::Missing => "display.patch.missing",
            Self::NotObject => "display.patch.not_object",
            Self::TooManyOps => "display.patch.too_many_ops",
            Self::TooDeep => "display.patch.too_deep",
            Self::Version => "display.patch.version",
        }
    }
}

impl std::fmt::Display for StreamError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for StreamError {}
