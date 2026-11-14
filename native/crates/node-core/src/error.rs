#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NodeError {
    Payload,
    TooLarge,
    TooMany,
    Key,
    Signature,
    Clock,
    Field,
    Hex,
}

impl NodeError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Payload => "node.error.payload",
            Self::TooLarge => "node.error.too_large",
            Self::TooMany => "node.error.too_many",
            Self::Key => "node.error.key",
            Self::Signature => "node.error.signature",
            Self::Clock => "node.error.clock",
            Self::Field => "node.error.field",
            Self::Hex => "node.error.hex",
        }
    }
}

pub type NodeResult<T> = Result<T, NodeError>;
