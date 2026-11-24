use std::collections::BTreeSet;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ValueType {
    Text,
    Number,
    Bool,
    File,
    Url,
    Contact,
    Image,
    Json,
    Time,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Effect {
    Read,
    Write,
    SendExternal,
    Spend,
    Physical,
}

impl Effect {
    pub const ALL: [Self; 5] = [
        Self::Read,
        Self::Write,
        Self::SendExternal,
        Self::Spend,
        Self::Physical,
    ];

    #[must_use]
    pub fn all() -> BTreeSet<Self> {
        Self::ALL.into_iter().collect()
    }

    #[must_use]
    pub fn irreversible_risk(self) -> bool {
        matches!(self, Self::SendExternal | Self::Spend | Self::Physical)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Role {
    Guest,
    Child,
    Staff,
    Family,
    Owner,
}

impl Role {
    #[must_use]
    pub fn permits(self, minimum: Self) -> bool {
        self >= minimum
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Origin {
    Local,
    Mcp,
    Node,
    Jev,
    Generated,
}

impl Origin {
    #[must_use]
    pub fn trusted(self) -> bool {
        matches!(self, Self::Local)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum State {
    Active,
    Degraded,
    Revoked,
}
