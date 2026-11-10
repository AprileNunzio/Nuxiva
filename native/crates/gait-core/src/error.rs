use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GaitError {
    InsufficientSamples,
    InsufficientDuration,
    InvalidBoundingBox,
    InvalidSignatureLength,
    InvalidSignatureValue,
    ArithmeticOverflow,
}

impl fmt::Display for GaitError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InsufficientSamples => write!(f, "gait: insufficient samples"),
            Self::InsufficientDuration => write!(f, "gait: observation duration too short"),
            Self::InvalidBoundingBox => write!(f, "gait: invalid bounding box coordinates"),
            Self::InvalidSignatureLength => write!(f, "gait: signature must have 16 dimensions"),
            Self::InvalidSignatureValue => write!(f, "gait: non-finite or out-of-range value in signature"),
            Self::ArithmeticOverflow => write!(f, "gait: numeric overflow during computation"),
        }
    }
}

impl std::error::Error for GaitError {}
