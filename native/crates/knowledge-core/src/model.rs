use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::embed::Vector;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    Person,
    Place,
    Object,
    Habit,
    Preference,
    Event,
    Concept,
}

impl Kind {
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Person => "person",
            Self::Place => "place",
            Self::Object => "object",
            Self::Habit => "habit",
            Self::Preference => "preference",
            Self::Event => "event",
            Self::Concept => "concept",
        }
    }

    pub const ALL: [Self; 7] = [
        Self::Person,
        Self::Place,
        Self::Object,
        Self::Habit,
        Self::Preference,
        Self::Event,
        Self::Concept,
    ];
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Level {
    Public,
    Family,
    Private,
    Secret,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Origin {
    User,
    Conversation,
    Document,
    Sensor,
    Inference,
}

impl Origin {
    #[must_use]
    pub const fn cap(self) -> u32 {
        match self {
            Self::User => 1000,
            Self::Conversation => 900,
            Self::Document => 850,
            Self::Sensor => 800,
            Self::Inference => 600,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Status {
    Active,
    Refuted,
    Superseded,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Provenance {
    pub origin: Origin,
    pub reference: String,
    pub at_ms: u64,
}

#[derive(Clone, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(transparent)]
pub struct NodeId(pub String);

#[derive(Clone, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(transparent)]
pub struct EdgeId(pub String);

impl std::fmt::Debug for NodeId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("NodeId(..)")
    }
}

impl std::fmt::Debug for EdgeId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("EdgeId(..)")
    }
}

fn hex_digest(parts: &[&str]) -> String {
    let mut hasher = Sha256::new();
    for part in parts {
        hasher.update(part.as_bytes());
        hasher.update([0]);
    }
    let digest = hasher.finalize();
    crate::text::hex(digest.get(..16).unwrap_or(&[]))
}

impl NodeId {
    #[must_use]
    pub fn derive(kind: Kind, key: &str) -> Self {
        Self(hex_digest(&["nuxiva.knowledge.node.v1", kind.name(), key]))
    }
}

impl EdgeId {
    #[must_use]
    pub fn derive(from: &NodeId, relation: &str, to: &NodeId) -> Self {
        Self(hex_digest(&[
            "nuxiva.knowledge.edge.v1",
            &from.0,
            relation,
            &to.0,
        ]))
    }
}

#[derive(Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case", tag = "form")]
pub enum Detail {
    Plain { text: String },
    Sealed { nonce: Vec<u8>, data: Vec<u8> },
}

impl std::fmt::Debug for Detail {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Detail(..)")
    }
}

#[derive(Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Node {
    pub id: NodeId,
    pub kind: Kind,
    pub key: String,
    pub label: String,
    pub detail: Option<Detail>,
    pub level: Level,
    pub confidence: u16,
    pub salience: u16,
    pub pinned: bool,
    pub created_ms: u64,
    pub updated_ms: u64,
    pub last_used_ms: u64,
    pub uses: u32,
    pub provenance: Vec<Provenance>,
    #[serde(skip)]
    pub vector: Vector,
}

impl std::fmt::Debug for Node {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Node(..)")
    }
}

#[derive(Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Edge {
    pub id: EdgeId,
    pub from: NodeId,
    pub to: NodeId,
    pub relation: String,
    pub level: Level,
    pub status: Status,
    pub confidence: u16,
    pub salience: u16,
    pub pinned: bool,
    pub created_ms: u64,
    pub updated_ms: u64,
    pub last_used_ms: u64,
    pub provenance: Vec<Provenance>,
}

impl std::fmt::Debug for Edge {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Edge(..)")
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NodeRef {
    pub kind: Kind,
    pub label: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Evidence {
    pub origin: Origin,
    #[serde(default)]
    pub reference: String,
    pub confidence: u32,
}

pub const SELF_KEY: &str = "@self";
