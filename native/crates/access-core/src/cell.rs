use crate::error::AccessError;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Cell {
    Allow,
    Room,
    Own,
    Confirm,
    Strong,
    Deny,
}

impl Cell {
    pub fn parse(raw: &str) -> Result<Self, AccessError> {
        match raw {
            "allow" => Ok(Self::Allow),
            "room" => Ok(Self::Room),
            "own" => Ok(Self::Own),
            "confirm" => Ok(Self::Confirm),
            "strong" => Ok(Self::Strong),
            "deny" => Ok(Self::Deny),
            _ => Err(AccessError::Cell),
        }
    }

    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Allow => "allow",
            Self::Room => "room",
            Self::Own => "own",
            Self::Confirm => "confirm",
            Self::Strong => "strong",
            Self::Deny => "deny",
        }
    }
}
