#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GestureError {
    LandmarkCount,
    LandmarkOutOfRange,
    TooManyHands,
    ProfileTooLarge,
    FrameTooLarge,
    FrameInvalid(String),
    ProfileInvalid(String),
    UnknownGesture(String),
    InvalidIdentifier(String),
}

impl GestureError {
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::LandmarkCount => "gesture.landmarks.count",
            Self::LandmarkOutOfRange => "gesture.landmarks.out_of_range",
            Self::TooManyHands => "gesture.frame.too_many_hands",
            Self::ProfileTooLarge => "gesture.profile.too_large",
            Self::FrameTooLarge => "gesture.frame.too_large",
            Self::FrameInvalid(_) => "gesture.frame.invalid",
            Self::ProfileInvalid(_) => "gesture.profile.invalid",
            Self::UnknownGesture(_) => "gesture.profile.unknown_gesture",
            Self::InvalidIdentifier(_) => "gesture.profile.invalid_identifier",
        }
    }
}

impl std::fmt::Display for GestureError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ProfileInvalid(detail)
            | Self::FrameInvalid(detail)
            | Self::UnknownGesture(detail)
            | Self::InvalidIdentifier(detail) => write!(f, "{}: {detail}", self.code()),
            _ => f.write_str(self.code()),
        }
    }
}

impl std::error::Error for GestureError {}
