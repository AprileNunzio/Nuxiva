use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Lifecycle {
    Dormant,
    Warm,
    Live,
    Frozen,
    Hibernated,
}

impl Lifecycle {
    #[must_use]
    pub const fn holds_gpu(self) -> bool {
        matches!(self, Self::Live | Self::Frozen)
    }

    #[must_use]
    pub const fn refreshes(self) -> bool {
        matches!(self, Self::Live | Self::Warm | Self::Hibernated)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Transition {
    pub instance: String,
    pub screen: u16,
    pub from: Lifecycle,
    pub to: Lifecycle,
    pub reason: &'static str,
}
