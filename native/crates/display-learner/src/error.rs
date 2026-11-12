use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LearnError {
    InvalidPerson,
    InvalidWidget,
    InvalidPolicy,
    InvalidSample,
    Capacity,
    Corrupt,
    Crypto,
    RandomUnavailable,
}

impl fmt::Display for LearnError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Self::InvalidPerson => "learner.person.invalid",
            Self::InvalidWidget => "learner.widget.invalid",
            Self::InvalidPolicy => "learner.policy.invalid",
            Self::InvalidSample => "learner.sample.invalid",
            Self::Capacity => "learner.capacity",
            Self::Corrupt => "learner.store.corrupt",
            Self::Crypto => "learner.store.crypto",
            Self::RandomUnavailable => "learner.random.unavailable",
        })
    }
}

impl std::error::Error for LearnError {}
