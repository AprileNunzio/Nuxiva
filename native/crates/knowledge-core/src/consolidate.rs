use std::collections::BTreeSet;

use nuxiva_context_core::PersonId;
use serde::Serialize;

use crate::error::{KnowledgeError, KnowledgeResult};
use crate::model::{Edge, EdgeId, Node, NodeId, SELF_KEY, Status};
use crate::num::{halve, noisy_or, to_u16};
use crate::store::{Knowledge, Partition, composite};
use crate::write::{push_provenance, read_detail, set_detail};

const MAX_ALIASES: usize = 10_000;
const MAX_CANDIDATES: usize = 64;
const OBSERVATION_TTL_MS: u64 = 180 * 86_400_000;

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize)]
pub struct Report {
    pub decayed: usize,
    pub merged: usize,
    pub forgotten_nodes: usize,
    pub forgotten_edges: usize,
}

impl Knowledge {
    pub fn consolidate(&mut self, who: &PersonId, now: u64) -> KnowledgeResult<Report> {
        self.own(who)?;
        let mut report = Report::default();
        self.decay(who, now, &mut report)?;
        self.merge(who, &mut report)?;
        self.forget(who, now, &mut report)?;
        let part = self
            .partitions
            .get_mut(who)
            .ok_or(KnowledgeError::NotFound)?;
        part.observations.retain(|_, samples| {
            samples.retain(|t| now.saturating_sub(*t) <= OBSERVATION_TTL_MS);
            !samples.is_empty()
        });
        Ok(report)
    }

    fn decay(&mut self, who: &PersonId, now: u64, report: &mut Report) -> KnowledgeResult<()> {
        let Self {
            settings,
            partitions,
            ..
        } = self;
        let part = partitions.get_mut(who).ok_or(KnowledgeError::NotFound)?;
        let elapsed = now.saturating_sub(part.last_decay_ms);
        let first = part.last_decay_ms == 0;
        part.last_decay_ms = now;
        if first || elapsed == 0 {
            return Ok(());
        }
        let kinds: std::collections::HashMap<NodeId, crate::model::Kind> = part
            .nodes
            .iter()
            .map(|(id, n)| (id.clone(), n.kind))
            .collect();
        for node in part.nodes.values_mut().filter(|n| !n.pinned) {
            let before = node.salience;
            node.salience = to_u16(halve(
                u32::from(before),
                elapsed,
                settings.half_life(node.kind),
            ));
            report.decayed = report
                .decayed
                .saturating_add(usize::from(before != node.salience));
        }
        for edge in part.edges.values_mut().filter(|e| !e.pinned) {
            let kind = kinds
                .get(&edge.from)
                .copied()
                .unwrap_or(crate::model::Kind::Concept);
            let before = edge.salience;
            edge.salience = to_u16(halve(u32::from(before), elapsed, settings.half_life(kind)));
            report.decayed = report
                .decayed
                .saturating_add(usize::from(before != edge.salience));
        }
        Ok(())
    }

    fn merge(&mut self, who: &PersonId, report: &mut Report) -> KnowledgeResult<()> {
        let threshold = self.settings.merge_threshold;
        let max = self.settings.max_merge_per_pass;
        let ids: Vec<NodeId> = self.own(who)?.nodes.keys().cloned().collect();
        let mut gone: BTreeSet<NodeId> = BTreeSet::new();
        for id in ids {
            if report.merged >= max {
                break;
            }
            if gone.contains(&id) {
                continue;
            }
            let Some(pair) = self.duplicate_of(who, &id, threshold, &gone)? else {
                continue;
            };
            let (keep, lose) = pair;
            self.fuse(who, &keep, &lose)?;
            gone.insert(lose);
            report.merged = report.merged.saturating_add(1);
        }
        Ok(())
    }

    fn duplicate_of(
        &self,
        who: &PersonId,
        id: &NodeId,
        threshold: u32,
        gone: &BTreeSet<NodeId>,
    ) -> KnowledgeResult<Option<(NodeId, NodeId)>> {
        let part = self.own(who)?;
        let Some(node) = part.nodes.get(id) else {
            return Ok(None);
        };
        if node.key == SELF_KEY {
            return Ok(None);
        }
        let mut seen: BTreeSet<&NodeId> = BTreeSet::new();
        for token in crate::text::tokens(&node.label) {
            for other in part.index.tokens.get(&token).into_iter().flatten() {
                if seen.len() >= MAX_CANDIDATES {
                    break;
                }
                seen.insert(other);
            }
        }
        for other in seen {
            if other == id || gone.contains(other) {
                continue;
            }
            let Some(candidate) = part.nodes.get(other) else {
                continue;
            };
            if candidate.kind != node.kind
                || candidate.key == SELF_KEY
                || (candidate.pinned && node.pinned)
                || node.vector.cosine_permille(&candidate.vector) < threshold
            {
                continue;
            }
            let rank = |n: &Node| (n.pinned, n.salience, std::cmp::Reverse(n.created_ms));
            let pair = if rank(node) >= rank(candidate) {
                (node.id.clone(), candidate.id.clone())
            } else {
                (candidate.id.clone(), node.id.clone())
            };
            return Ok(Some(pair));
        }
        Ok(None)
    }

    fn fuse(&mut self, who: &PersonId, keep: &NodeId, lose: &NodeId) -> KnowledgeResult<()> {
        let Self {
            settings,
            key,
            partitions,
        } = self;
        let part = partitions.get_mut(who).ok_or(KnowledgeError::NotFound)?;
        let owner = part.owner.clone();
        let loser = part
            .nodes
            .get(lose)
            .cloned()
            .ok_or(KnowledgeError::NotFound)?;
        let plain = read_detail(key.as_deref(), &owner, &loser)?;
        let incident: Vec<Edge> = [true, false]
            .iter()
            .flat_map(|out| part.edges_of(lose, *out).cloned())
            .collect();
        for edge in &incident {
            part.drop_edge(&edge.id);
        }
        let alias = composite(loser.kind, &loser.key);
        part.unindex_tokens(lose);
        part.nodes.remove(lose);
        part.index.keys.remove(&alias);
        if part.aliases.len() < MAX_ALIASES {
            part.aliases.insert(alias.clone(), keep.clone());
        }
        part.index.keys.insert(alias, keep.clone());
        let winner = part.nodes.get_mut(keep).ok_or(KnowledgeError::Corrupt)?;
        winner.confidence = to_u16(noisy_or(
            u32::from(winner.confidence),
            u32::from(loser.confidence),
        ));
        winner.salience = winner.salience.max(loser.salience);
        winner.level = winner.level.max(loser.level);
        winner.pinned |= loser.pinned;
        winner.uses = winner.uses.saturating_add(loser.uses);
        winner.last_used_ms = winner.last_used_ms.max(loser.last_used_ms);
        winner.created_ms = winner.created_ms.min(loser.created_ms);
        for item in loser.provenance.iter().cloned() {
            push_provenance(&mut winner.provenance, item, settings.max_provenance);
        }
        if winner.detail.is_none() {
            set_detail(key.as_deref(), &owner, winner, plain.as_deref())?;
        } else {
            crate::write::reseal(key.as_deref(), &owner, winner)?;
        }
        part.refresh(keep);
        for edge in incident {
            rewire(part, edge, lose, keep, settings.max_provenance);
        }
        Ok(())
    }

    fn forget(&mut self, who: &PersonId, now: u64, report: &mut Report) -> KnowledgeResult<()> {
        let floor = u16::try_from(self.settings.forget_floor).unwrap_or(0);
        let min_age = self.settings.forget_min_age_ms;
        let mut budget = self.settings.max_forget_per_pass;
        let part = self
            .partitions
            .get_mut(who)
            .ok_or(KnowledgeError::NotFound)?;
        let age = |created: u64, used: u64| now.saturating_sub(created.max(used));
        let mut edges: Vec<(u16, EdgeId)> = part
            .edges
            .values()
            .filter(|e| {
                !e.pinned && e.salience < floor && age(e.created_ms, e.last_used_ms) >= min_age
            })
            .map(|e| (e.salience, e.id.clone()))
            .collect();
        edges.sort();
        for (_, id) in edges.into_iter().take(budget) {
            part.drop_edge(&id);
            budget = budget.saturating_sub(1);
            report.forgotten_edges = report.forgotten_edges.saturating_add(1);
        }
        let mut nodes: Vec<(u16, NodeId)> = part
            .nodes
            .values()
            .filter(|n| {
                !n.pinned
                    && n.key != SELF_KEY
                    && n.salience < floor
                    && age(n.created_ms, n.last_used_ms) >= min_age
            })
            .map(|n| (n.salience, n.id.clone()))
            .collect();
        nodes.sort();
        for (_, id) in nodes.into_iter().take(budget) {
            let incident = [&part.index.out, &part.index.inn]
                .iter()
                .filter_map(|m| m.get(&id))
                .map(Vec::len)
                .fold(0_usize, usize::saturating_add);
            part.drop_node(&id);
            report.forgotten_nodes = report.forgotten_nodes.saturating_add(1);
            report.forgotten_edges = report.forgotten_edges.saturating_add(incident);
        }
        Ok(())
    }
}

fn rewire(part: &mut Partition, edge: Edge, lose: &NodeId, keep: &NodeId, max_provenance: usize) {
    let from = if edge.from == *lose {
        keep.clone()
    } else {
        edge.from.clone()
    };
    let to = if edge.to == *lose {
        keep.clone()
    } else {
        edge.to.clone()
    };
    if from == to {
        return;
    }
    let id = EdgeId::derive(&from, &edge.relation, &to);
    if let Some(existing) = part.edges.get_mut(&id) {
        if existing.status == Status::Active || edge.status != Status::Active {
            existing.confidence = to_u16(noisy_or(
                u32::from(existing.confidence),
                u32::from(edge.confidence),
            ));
        }
        existing.salience = existing.salience.max(edge.salience);
        existing.pinned |= edge.pinned;
        for item in edge.provenance {
            push_provenance(&mut existing.provenance, item, max_provenance);
        }
        return;
    }
    let moved = Edge {
        id: id.clone(),
        from: from.clone(),
        to: to.clone(),
        ..edge
    };
    part.edges.insert(id.clone(), moved);
    part.link(id, from, to);
}
