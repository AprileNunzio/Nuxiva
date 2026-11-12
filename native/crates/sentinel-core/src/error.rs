use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SentinelError {
    InvalidEvent(&'static str),
    InvalidDay,
    InvalidKey,
    InvalidQuery(&'static str),
    InvalidPolicy,
    Broken(usize),
    Truncated,
    Crypto,
    Signature,
    RandomUnavailable,
    TooLarge,
}

impl fmt::Display for SentinelError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidEvent(why) => write!(f, "sentinel.event.invalid: {why}"),
            Self::InvalidDay => f.write_str("sentinel.day.invalid"),
            Self::InvalidKey => f.write_str("sentinel.key.invalid"),
            Self::InvalidQuery(why) => write!(f, "sentinel.query.invalid: {why}"),
            Self::InvalidPolicy => f.write_str("sentinel.retention.invalid"),
            Self::Broken(at) => write!(f, "sentinel.chain.broken: {at}"),
            Self::Truncated => f.write_str("sentinel.journal.truncated"),
            Self::Crypto => f.write_str("sentinel.crypto"),
            Self::Signature => f.write_str("sentinel.signature"),
            Self::RandomUnavailable => f.write_str("sentinel.random.unavailable"),
            Self::TooLarge => f.write_str("sentinel.too_large"),
        }
    }
}

impl std::error::Error for SentinelError {}
