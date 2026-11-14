use nuxiva_context_core::{PersonId, Role};
use serde::Deserialize;

use crate::correct::Correction;
use crate::extract::Fact;
use crate::model::{Kind, Level, NodeRef, Origin};
use crate::read::{NeighborQuery, Query};

pub const MAX_REQUEST: usize = 256 * 1024;

const fn yes() -> bool {
    true
}

const fn conversation() -> Origin {
    Origin::Conversation
}

const fn private() -> Level {
    Level::Private
}

const fn default_confidence() -> u32 {
    800
}

#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case", deny_unknown_fields)]
pub enum Command {
    Register {
        id: PersonId,
        name: String,
        role: Role,
        #[serde(default = "yes")]
        consent: bool,
    },
    Remember {
        #[serde(rename = "as")]
        who: PersonId,
        kind: Kind,
        label: String,
        #[serde(default)]
        detail: Option<String>,
        #[serde(default = "private")]
        level: Level,
        #[serde(default = "default_confidence")]
        confidence: u32,
        #[serde(default = "conversation")]
        origin: Origin,
        #[serde(default)]
        reference: String,
    },
    Relate {
        #[serde(rename = "as")]
        who: PersonId,
        from: NodeRef,
        relation: String,
        to: NodeRef,
        #[serde(default = "private")]
        level: Level,
        #[serde(default = "default_confidence")]
        confidence: u32,
        #[serde(default = "conversation")]
        origin: Origin,
        #[serde(default)]
        reference: String,
    },
    Correct {
        #[serde(rename = "as")]
        who: PersonId,
        correction: Correction,
    },
    Search {
        #[serde(rename = "as")]
        who: PersonId,
        query: Query,
    },
    Neighbors {
        #[serde(rename = "as")]
        who: PersonId,
        query: NeighborQuery,
    },
    Path {
        #[serde(rename = "as")]
        who: PersonId,
        from: NodeRef,
        to: NodeRef,
    },
    Extract {
        #[serde(rename = "as")]
        who: PersonId,
        text: String,
        #[serde(default = "conversation")]
        origin: Origin,
        #[serde(default)]
        reference: String,
        #[serde(default = "yes")]
        store: bool,
    },
    Ingest {
        #[serde(rename = "as")]
        who: PersonId,
        facts: Vec<Fact>,
        origin: Origin,
        #[serde(default)]
        reference: String,
    },
    Observe {
        #[serde(rename = "as")]
        who: PersonId,
        label: String,
    },
    Consolidate {
        #[serde(rename = "as")]
        who: PersonId,
    },
    Export {
        #[serde(rename = "as")]
        who: PersonId,
    },
    Erase {
        #[serde(rename = "as")]
        who: PersonId,
        confirm: String,
    },
    Stats {
        #[serde(rename = "as")]
        who: PersonId,
    },
    Persist {
        #[serde(rename = "as")]
        who: PersonId,
    },
    Restore {
        id: PersonId,
    },
}
