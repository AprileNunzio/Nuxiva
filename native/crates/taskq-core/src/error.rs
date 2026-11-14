#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TaskqError {
    Parse,
    TooLarge,
    Invalid,
    Version,
    Full,
    UnknownDep,
    DepFailed,
    UnknownParent,
    Settings,
    Serialize,
    Journal,
    Tamper,
    NotFound,
    Terminal,
    Shutdown,
}

impl TaskqError {
    const ALL: [Self; 15] = [
        Self::Parse,
        Self::TooLarge,
        Self::Invalid,
        Self::Version,
        Self::Full,
        Self::UnknownDep,
        Self::DepFailed,
        Self::UnknownParent,
        Self::Settings,
        Self::Serialize,
        Self::Journal,
        Self::Tamper,
        Self::NotFound,
        Self::Terminal,
        Self::Shutdown,
    ];

    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Parse => "taskq.parse",
            Self::TooLarge => "taskq.too_large",
            Self::Invalid => "taskq.invalid",
            Self::Version => "taskq.version",
            Self::Full => "taskq.full",
            Self::UnknownDep => "taskq.unknown_dep",
            Self::DepFailed => "taskq.dep_failed",
            Self::UnknownParent => "taskq.unknown_parent",
            Self::Settings => "taskq.settings.invalid",
            Self::Serialize => "taskq.serialize",
            Self::Journal => "taskq.journal",
            Self::Tamper => "taskq.journal.tamper",
            Self::NotFound => "taskq.not_found",
            Self::Terminal => "taskq.terminal",
            Self::Shutdown => "taskq.shutdown",
        }
    }

    #[must_use]
    pub fn from_code(code: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|e| e.code() == code)
    }
}

impl std::fmt::Display for TaskqError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for TaskqError {}

pub type TaskqResult<T> = Result<T, TaskqError>;
