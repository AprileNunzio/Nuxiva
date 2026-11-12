use serde::{Deserialize, Serialize};

pub const COLUMNS: usize = 6;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Role {
    System,
    Owner,
    Family,
    Staff,
    Child,
    Guest,
    Anonymous,
}

impl Role {
    #[must_use]
    pub fn parse(raw: &str) -> Self {
        match raw {
            "system" => Self::System,
            "owner" => Self::Owner,
            "family" => Self::Family,
            "staff" | "friend" => Self::Staff,
            "child" => Self::Child,
            "guest" => Self::Guest,
            _ => Self::Anonymous,
        }
    }

    #[must_use]
    pub const fn column(self) -> Option<usize> {
        match self {
            Self::System => None,
            Self::Owner => Some(0),
            Self::Family => Some(1),
            Self::Staff => Some(2),
            Self::Child => Some(3),
            Self::Guest => Some(4),
            Self::Anonymous => Some(5),
        }
    }

    #[must_use]
    pub const fn outsider(self) -> bool {
        matches!(self, Self::Guest | Self::Anonymous)
    }
}
