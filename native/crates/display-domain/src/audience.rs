use crate::sensitivity::Sensitivity;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AudienceKind {
    Empty,
    GuestOnly,
    Authorized,
    Mixed,
    Uncertain,
}

impl AudienceKind {
    #[must_use]
    pub const fn may_see(self, level: Sensitivity, trust_guests: bool) -> bool {
        match self {
            Self::Authorized => true,
            Self::Mixed => {
                matches!(level, Sensitivity::Public)
                    || (trust_guests && matches!(level, Sensitivity::Household))
            }
            Self::GuestOnly | Self::Empty | Self::Uncertain => false,
        }
    }

    #[must_use]
    pub const fn nucleus_only(self) -> bool {
        matches!(self, Self::Empty | Self::GuestOnly | Self::Uncertain)
    }
}
