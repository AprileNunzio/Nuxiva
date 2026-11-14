use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Background {
    None,
    Radio,
    Music,
    Tv,
}

impl Background {
    #[must_use]
    pub fn is_noisy(self) -> bool {
        self != Self::None
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Class {
    Known,
    Guest,
    Broadcast,
}

impl Class {
    #[must_use]
    pub fn index(self) -> usize {
        match self {
            Self::Known => 0,
            Self::Guest => 1,
            Self::Broadcast => 2,
        }
    }

    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            Self::Known => "known",
            Self::Guest => "guest",
            Self::Broadcast => "broadcast",
        }
    }
}
