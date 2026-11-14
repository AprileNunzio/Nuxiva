use std::collections::BTreeMap;

use nuxiva_context_core::{PersonId, Role};
use serde::Serialize;
use zeroize::Zeroize;

use crate::error::{KnowledgeError, KnowledgeResult};
use crate::model::{Edge, Kind, Level, NodeId, Provenance};
use crate::store::Knowledge;
use crate::write::read_detail;

pub const EXPORT_SCHEMA: u8 = 1;

#[derive(Debug, Clone, Serialize)]
pub struct ExportNode {
    pub id: NodeId,
    pub kind: Kind,
    pub label: String,
    pub detail: Option<String>,
    pub level: Level,
    pub confidence: u16,
    pub salience: u16,
    pub pinned: bool,
    pub created_ms: u64,
    pub updated_ms: u64,
    pub provenance: Vec<Provenance>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ExportBundle {
    pub schema: u8,
    pub owner: PersonId,
    pub name: String,
    pub role: Role,
    pub nodes: Vec<ExportNode>,
    pub edges: Vec<Edge>,
    pub observations: BTreeMap<String, Vec<u64>>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct Receipt {
    pub nodes: usize,
    pub edges: usize,
    pub observations: usize,
}

#[must_use]
pub fn confirmation(who: &PersonId) -> String {
    format!("ERASE:{}", who.as_str())
}

impl Knowledge {
    pub fn export(&self, who: &PersonId) -> KnowledgeResult<ExportBundle> {
        let part = self.own(who)?;
        let mut nodes = Vec::with_capacity(part.nodes.len());
        for node in part.nodes.values() {
            nodes.push(ExportNode {
                id: node.id.clone(),
                kind: node.kind,
                label: node.label.clone(),
                detail: read_detail(self.key.as_deref(), &part.owner, node)?,
                level: node.level,
                confidence: node.confidence,
                salience: node.salience,
                pinned: node.pinned,
                created_ms: node.created_ms,
                updated_ms: node.updated_ms,
                provenance: node.provenance.clone(),
            });
        }
        Ok(ExportBundle {
            schema: EXPORT_SCHEMA,
            owner: part.owner.clone(),
            name: part.name.clone(),
            role: part.role,
            nodes,
            edges: part.edges.values().cloned().collect(),
            observations: part.observations.clone(),
        })
    }

    pub fn erase(&mut self, who: &PersonId, confirm: &str) -> KnowledgeResult<Receipt> {
        if confirm != confirmation(who) {
            return Err(KnowledgeError::Confirm);
        }
        let mut part = self
            .partitions
            .remove(who)
            .ok_or(KnowledgeError::NotFound)?;
        let receipt = Receipt {
            nodes: part.nodes.len(),
            edges: part.edges.len(),
            observations: part.observations.len(),
        };
        for node in part.nodes.values_mut() {
            node.label.zeroize();
            node.key.zeroize();
            node.detail = None;
        }
        part.name.zeroize();
        Ok(receipt)
    }
}
