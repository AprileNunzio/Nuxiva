use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    Agent,
    Tool,
    Intent,
    Widget,
    Mcp,
    Node,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Origin {
    System,
    User,
    Generated,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum State {
    Active,
    Degraded,
    Revoked,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Found {
    pub id: String,
    pub origin: Origin,
    pub hash: [u8; 32],
}

impl Found {
    #[must_use]
    pub fn new(id: &str, origin: Origin, content: &[u8]) -> Self {
        Self {
            id: id.to_owned(),
            origin,
            hash: *blake3::hash(content).as_bytes(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Item {
    pub kind: Kind,
    pub id: String,
    pub origin: Origin,
    pub hash: [u8; 32],
    pub state: State,
    pub first_seen_ms: u64,
    pub last_seen_ms: u64,
    pub verified: bool,
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Diff {
    pub added: Vec<String>,
    pub changed: Vec<String>,
    pub missing: Vec<String>,
    pub revoked: Vec<String>,
    pub rejected: Vec<String>,
}

impl Diff {
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.added.is_empty()
            && self.changed.is_empty()
            && self.missing.is_empty()
            && self.revoked.is_empty()
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Snapshot {
    pub generation: u64,
    pub items: Vec<Item>,
}
