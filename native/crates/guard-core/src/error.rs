#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GuardError {
    WeakSecret,
    Username,
    Lifetime,
    EnvKey,
    EnvValue,
}

impl GuardError {
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::WeakSecret => "guard.secret.weak",
            Self::Username => "guard.username.invalid",
            Self::Lifetime => "guard.lifetime.invalid",
            Self::EnvKey => "guard.env.key",
            Self::EnvValue => "guard.env.value",
        }
    }
}

impl std::fmt::Display for GuardError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for GuardError {}

pub type GuardResult<T> = Result<T, GuardError>;
