#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TokenError {
    WeakSecret,
    Subject,
    Lifetime,
    Claims,
    TooLarge,
    Format,
    Signature,
    Payload,
    Expired,
    NotYetValid,
}

impl TokenError {
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::WeakSecret => "token.secret.weak",
            Self::Subject => "token.subject.invalid",
            Self::Lifetime => "token.lifetime.invalid",
            Self::Claims => "token.claims.invalid",
            Self::TooLarge => "token.too_large",
            Self::Format => "token.format",
            Self::Signature => "token.signature",
            Self::Payload => "token.payload",
            Self::Expired => "token.expired",
            Self::NotYetValid => "token.not_yet_valid",
        }
    }
}

impl std::fmt::Display for TokenError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for TokenError {}

pub type TokenResult<T> = Result<T, TokenError>;
