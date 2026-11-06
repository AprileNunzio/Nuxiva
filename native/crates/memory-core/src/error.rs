use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MemoryError {
    InvalidSighting(&'static str),
    InvalidSearch(&'static str),
    InvalidPolicy,
    InvalidKey,
    Broken(usize),
    Crypto,
    TooLarge,
    Sentinel(String),
}

impl fmt::Display for MemoryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidSighting(why) => write!(f, "memory.sighting.invalid: {why}"),
            Self::InvalidSearch(why) => write!(f, "memory.search.invalid: {why}"),
            Self::InvalidPolicy => f.write_str("memory.retention.invalid"),
            Self::InvalidKey => f.write_str("memory.key.invalid"),
            Self::Broken(at) => write!(f, "memory.chain.broken: {at}"),
            Self::Crypto => f.write_str("memory.crypto"),
            Self::TooLarge => f.write_str("memory.too_large"),
            Self::Sentinel(why) => write!(f, "memory.sentinel: {why}"),
        }
    }
}

impl std::error::Error for MemoryError {}

impl From<nuxiva_sentinel_core::SentinelError> for MemoryError {
    fn from(value: nuxiva_sentinel_core::SentinelError) -> Self {
        Self::Sentinel(value.to_string())
    }
}
