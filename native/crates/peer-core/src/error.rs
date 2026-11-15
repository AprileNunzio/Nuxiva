#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PeerError {
    Field,
    Limit,
    Unknown,
    Untrusted,
    Signature,
    Clock,
    Replay,
    Payload,
    Key,
    Capacity,
    State,
}

impl PeerError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Field => "peer.error.field",
            Self::Limit => "peer.error.limit",
            Self::Unknown => "peer.error.unknown",
            Self::Untrusted => "peer.error.untrusted",
            Self::Signature => "peer.error.signature",
            Self::Clock => "peer.error.clock",
            Self::Replay => "peer.error.replay",
            Self::Payload => "peer.error.payload",
            Self::Key => "peer.error.key",
            Self::Capacity => "peer.error.capacity",
            Self::State => "peer.error.state",
        }
    }
}

pub type PeerResult<T> = Result<T, PeerError>;
