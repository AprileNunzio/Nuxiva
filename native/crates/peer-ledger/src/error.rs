use nuxiva_peer_core::PeerError;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LedgerError {
    Field,
    Limit,
    Untrusted,
    Signature,
    Link,
    Gap,
    Fork,
    Clock,
    Capacity,
    Storage,
    Corrupt,
}

impl LedgerError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Field => "ledger.error.field",
            Self::Limit => "ledger.error.limit",
            Self::Untrusted => "ledger.error.untrusted",
            Self::Signature => "ledger.error.signature",
            Self::Link => "ledger.error.link",
            Self::Gap => "ledger.error.gap",
            Self::Fork => "ledger.error.fork",
            Self::Clock => "ledger.error.clock",
            Self::Capacity => "ledger.error.capacity",
            Self::Storage => "ledger.error.storage",
            Self::Corrupt => "ledger.error.corrupt",
        }
    }
}

impl From<PeerError> for LedgerError {
    fn from(error: PeerError) -> Self {
        match error {
            PeerError::Limit => Self::Limit,
            PeerError::Untrusted => Self::Untrusted,
            PeerError::Signature => Self::Signature,
            PeerError::Capacity => Self::Capacity,
            _ => Self::Field,
        }
    }
}

pub type LedgerResult<T> = Result<T, LedgerError>;
