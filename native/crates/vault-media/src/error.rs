use std::fmt;

#[derive(Debug, PartialEq, Eq)]
pub enum MediaVaultError {
    Crypto(String),
    Serialization(String),
    InvalidHeader,
    ChunkCorrupted,
    KeyDerivation,
    RetentionExpired,
    CorruptedPayload,
    InvalidRange,
    Io(String),
}

impl fmt::Display for MediaVaultError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Crypto(msg) => write!(f, "media vault crypto error: {msg}"),
            Self::Serialization(msg) => write!(f, "serialization error: {msg}"),
            Self::InvalidHeader => write!(f, "invalid segment header"),
            Self::ChunkCorrupted => write!(f, "chunk authentication failed or corrupted"),
            Self::KeyDerivation => write!(f, "key derivation failed"),
            Self::RetentionExpired => write!(f, "segment retention expired"),
            Self::CorruptedPayload => write!(f, "corrupted media payload"),
            Self::InvalidRange => write!(f, "invalid byte or chunk range"),
            Self::Io(msg) => write!(f, "io error: {msg}"),
        }
    }
}

impl std::error::Error for MediaVaultError {}

pub type MediaVaultResult<T> = Result<T, MediaVaultError>;
