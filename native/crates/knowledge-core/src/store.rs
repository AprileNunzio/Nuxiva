use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::sync::Arc;

use nuxiva_context_core::{PersonId, Role};
use serde::{Deserialize, Serialize};

use crate::embed::embed;
use crate::error::{KnowledgeError, KnowledgeResult};
use crate::model::{Detail, Edge, EdgeId, Kind, Level, Node, NodeId};
use crate::seal::MasterKey;
use crate::settings::KnowledgeSettings;
use crate::text::tokens;

#[derive(Debug, Default)]
pub struct Index {
    pub out: HashMap<NodeId, Vec<EdgeId>>,
    pub inn: HashMap<NodeId, Vec<EdgeId>>,
    pub tokens: HashMap<String, BTreeSet<NodeId>>,
    pub keys: HashMap<String, NodeId>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Partition {
    pub owner: PersonId,
    pub name: String,
    pub role: Role,
    pub consent: bool,
    pub nodes: BTreeMap<NodeId, Node>,
    pub edges: BTreeMap<EdgeId, Edge>,
    pub observations: BTreeMap<String, Vec<u64>>,
    #[serde(default)]
    pub blocked: BTreeSet<String>,
    #[serde(default)]
    pub aliases: BTreeMap<String, NodeId>,
    #[serde(default)]
    pub last_decay_ms: u64,
    #[serde(skip)]
    pub index: Index,
}

impl std::fmt::Debug for Partition {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Partition(..)")
    }
}

pub fn composite(kind: Kind, key: &str) -> String {
    format!("{}\0{key}", kind.name())
}

pub fn searchable(node: &Node) -> String {
    match (&node.detail, node.level) {
        (Some(Detail::Plain { text }), level) if level < Level::Secret => {
            format!("{} {text}", node.label)
        }
        _ => node.label.clone(),
    }
}

impl Partition {
    #[must_use]
    pub fn new(owner: PersonId, name: String, role: Role, consent: bool) -> Self {
        Self {
            owner,
            name,
            role,
            consent,
            nodes: BTreeMap::new(),
            edges: BTreeMap::new(),
            observations: BTreeMap::new(),
            blocked: BTreeSet::new(),
            aliases: BTreeMap::new(),
            last_decay_ms: 0,
            index: Index::default(),
        }
    }

    pub fn reindex(&mut self) {
        self.index = Index::default();
        let ids: Vec<NodeId> = self.nodes.keys().cloned().collect();
        for id in ids {
            self.refresh(&id);
        }
        let aliases: Vec<(String, NodeId)> = self
            .aliases
            .iter()
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect();
        for (key, id) in aliases {
            if self.nodes.contains_key(&id) {
                self.index.keys.entry(key).or_insert(id);
            }
        }
        let edges: Vec<(EdgeId, NodeId, NodeId)> = self
            .edges
            .values()
            .map(|e| (e.id.clone(), e.from.clone(), e.to.clone()))
            .collect();
        for (id, from, to) in edges {
            self.link(id, from, to);
        }
    }

    pub fn refresh(&mut self, id: &NodeId) {
        self.unindex_tokens(id);
        let Some(node) = self.nodes.get_mut(id) else {
            return;
        };
        let text = searchable(node);
        node.vector = embed(&text);
        let key = composite(node.kind, &node.key);
        self.index.keys.insert(key, id.clone());
        for token in tokens(&text) {
            self.index
                .tokens
                .entry(token)
                .or_default()
                .insert(id.clone());
        }
    }

    pub fn unindex_tokens(&mut self, id: &NodeId) {
        let Some(node) = self.nodes.get(id) else {
            return;
        };
        for token in tokens(&searchable(node)) {
            if let Some(set) = self.index.tokens.get_mut(&token) {
                set.remove(id);
                if set.is_empty() {
                    self.index.tokens.remove(&token);
                }
            }
        }
    }

    pub fn link(&mut self, id: EdgeId, from: NodeId, to: NodeId) {
        self.index.out.entry(from).or_default().push(id.clone());
        self.index.inn.entry(to).or_default().push(id);
    }

    pub fn drop_edge(&mut self, id: &EdgeId) {
        let Some(edge) = self.edges.remove(id) else {
            return;
        };
        for (map, node) in [
            (&mut self.index.out, &edge.from),
            (&mut self.index.inn, &edge.to),
        ] {
            if let Some(list) = map.get_mut(node) {
                list.retain(|e| e != id);
                if list.is_empty() {
                    map.remove(node);
                }
            }
        }
    }

    pub fn drop_node(&mut self, id: &NodeId) {
        let mut incident: Vec<EdgeId> = Vec::new();
        for map in [&self.index.out, &self.index.inn] {
            if let Some(list) = map.get(id) {
                incident.extend(list.iter().cloned());
            }
        }
        for edge in incident {
            self.drop_edge(&edge);
        }
        self.unindex_tokens(id);
        if let Some(node) = self.nodes.remove(id) {
            self.index.keys.remove(&composite(node.kind, &node.key));
        }
    }

    #[must_use]
    pub fn find(&self, kind: Kind, key: &str) -> Option<&NodeId> {
        self.index.keys.get(&composite(kind, key))
    }

    pub fn edges_of<'a>(
        &'a self,
        id: &NodeId,
        outgoing: bool,
    ) -> impl Iterator<Item = &'a Edge> + 'a {
        let map = if outgoing {
            &self.index.out
        } else {
            &self.index.inn
        };
        map.get(id)
            .into_iter()
            .flatten()
            .filter_map(|e| self.edges.get(e))
    }
}

#[derive(Debug)]
pub struct Knowledge {
    pub settings: KnowledgeSettings,
    pub key: Option<Arc<MasterKey>>,
    pub partitions: HashMap<PersonId, Partition>,
}

impl Knowledge {
    pub fn new(settings: KnowledgeSettings, key: Option<Arc<MasterKey>>) -> KnowledgeResult<Self> {
        settings.validate()?;
        Ok(Self {
            settings,
            key,
            partitions: HashMap::new(),
        })
    }

    pub fn register(
        &mut self,
        id: &PersonId,
        name: &str,
        role: Role,
        consent: bool,
    ) -> KnowledgeResult<()> {
        let name = crate::text::clean(name, self.settings.max_label_chars)?;
        if let Some(existing) = self.partitions.get_mut(id) {
            existing.name = name;
            existing.role = role;
            existing.consent = consent;
            return Ok(());
        }
        if self.partitions.len() >= self.settings.max_partitions {
            return Err(KnowledgeError::Capacity);
        }
        self.partitions
            .insert(id.clone(), Partition::new(id.clone(), name, role, consent));
        Ok(())
    }

    pub fn install(&mut self, partition: Partition) -> KnowledgeResult<()> {
        if !self.partitions.contains_key(&partition.owner)
            && self.partitions.len() >= self.settings.max_partitions
        {
            return Err(KnowledgeError::Capacity);
        }
        let mut partition = partition;
        partition.reindex();
        self.partitions.insert(partition.owner.clone(), partition);
        Ok(())
    }

    pub fn partition(&self, id: &PersonId) -> KnowledgeResult<&Partition> {
        self.partitions.get(id).ok_or(KnowledgeError::NotFound)
    }

    #[must_use]
    pub fn total_nodes(&self) -> usize {
        self.partitions
            .values()
            .map(|p| p.nodes.len())
            .fold(0_usize, usize::saturating_add)
    }

    #[must_use]
    pub fn total_edges(&self) -> usize {
        self.partitions
            .values()
            .map(|p| p.edges.len())
            .fold(0_usize, usize::saturating_add)
    }
}
