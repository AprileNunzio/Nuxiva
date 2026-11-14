use std::collections::{BTreeMap, BTreeSet, HashMap, VecDeque};

use nuxiva_context_core::PersonId;
use serde::{Deserialize, Serialize};

use crate::embed::embed;
use crate::error::{KnowledgeError, KnowledgeResult};
use crate::model::{EdgeId, Kind, Level, Node, NodeId, NodeRef, Status};
use crate::num::{noisy_or, scale, to_u16};
use crate::store::{Knowledge, Partition};
use crate::text::{relation_name, tokens};
use crate::write::{key_of, read_detail};

const MAX_EXPANSION: usize = 256;
const MAX_POSTING: u32 = 2_048;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Query {
    pub text: String,
    pub kinds: Vec<Kind>,
    pub limit: usize,
    pub depth: usize,
    pub household: bool,
    pub min_confidence: u32,
    pub reveal: bool,
}

impl Default for Query {
    fn default() -> Self {
        Self {
            text: String::new(),
            kinds: Vec::new(),
            limit: 10,
            depth: 1,
            household: false,
            min_confidence: 0,
            reveal: false,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Hit {
    pub owner: PersonId,
    pub id: NodeId,
    pub kind: Kind,
    pub label: String,
    pub detail: Option<String>,
    pub level: Level,
    pub confidence: u16,
    pub salience: u16,
    pub pinned: bool,
    pub score: u32,
    pub via: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Direction {
    Out,
    In,
    Both,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct NeighborQuery {
    pub node: Option<NodeRef>,
    pub relation: Option<String>,
    pub direction: Direction,
    pub limit: usize,
    pub reveal: bool,
}

impl Default for NeighborQuery {
    fn default() -> Self {
        Self {
            node: None,
            relation: None,
            direction: Direction::Both,
            limit: 20,
            reveal: false,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Related {
    pub edge: EdgeId,
    pub relation: String,
    pub outgoing: bool,
    pub status: Status,
    pub confidence: u16,
    pub pinned: bool,
    pub node: Hit,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Step {
    pub from: String,
    pub relation: String,
    pub outgoing: bool,
    pub to: String,
}

fn weight(node: &Node) -> u32 {
    scale(u32::from(node.confidence), u32::from(node.salience))
}

impl Knowledge {
    fn hit(
        &self,
        part: &Partition,
        node: &Node,
        score: u32,
        via: Option<String>,
        reveal: bool,
    ) -> KnowledgeResult<Hit> {
        let detail = if node.level == Level::Secret && !reveal {
            None
        } else {
            read_detail(self.key.as_deref(), &part.owner, node)?
        };
        Ok(Hit {
            owner: part.owner.clone(),
            id: node.id.clone(),
            kind: node.kind,
            label: node.label.clone(),
            detail,
            level: node.level,
            confidence: node.confidence,
            salience: node.salience,
            pinned: node.pinned,
            score,
            via,
        })
    }

    pub fn search(&self, who: &PersonId, query: &Query) -> KnowledgeResult<Vec<Hit>> {
        let s = &self.settings;
        if query.limit == 0 || query.limit > s.max_limit || query.depth > s.max_depth {
            return Err(KnowledgeError::Invalid);
        }
        if query.text.chars().any(char::is_control) || query.text.chars().count() > 400 {
            return Err(KnowledgeError::Invalid);
        }
        let own = self.own(who)?;
        let qvec = embed(&query.text);
        let qtokens: BTreeSet<String> = tokens(&query.text).into_iter().collect();
        let mut best: BTreeMap<(PersonId, NodeId), Hit> = BTreeMap::new();
        let mut parts = vec![(own, Level::Secret)];
        if query.household {
            parts = self.visible(who, true);
        }
        for (part, ceiling) in parts {
            let reveal = query.reveal && part.owner == *who;
            let mut seeds = self.seeds(part, ceiling, &qvec, &qtokens, query);
            seeds.sort_by(|a, b| b.1.cmp(&a.1).then_with(|| a.0.cmp(&b.0)));
            seeds.truncate(query.limit.saturating_mul(2).max(8));
            let mut found: HashMap<NodeId, (u32, Option<String>)> = HashMap::new();
            for (id, score) in &seeds {
                found.insert(id.clone(), (*score, None));
            }
            for (id, score) in &seeds {
                self.expand(part, ceiling, id, *score, query.depth, &mut found);
            }
            for (id, (score, via)) in found {
                let Some(node) = part.nodes.get(&id) else {
                    continue;
                };
                if node.level > ceiling
                    || u32::from(node.confidence) < query.min_confidence
                    || !(query.kinds.is_empty() || query.kinds.contains(&node.kind))
                {
                    continue;
                }
                let hit = self.hit(part, node, score, via, reveal)?;
                best.insert((part.owner.clone(), id), hit);
            }
        }
        let mut hits: Vec<Hit> = best.into_values().collect();
        hits.sort_by(|a, b| {
            b.score
                .cmp(&a.score)
                .then_with(|| a.owner.cmp(&b.owner))
                .then_with(|| a.id.cmp(&b.id))
        });
        hits.truncate(query.limit);
        Ok(hits)
    }

    fn seeds(
        &self,
        part: &Partition,
        ceiling: Level,
        qvec: &crate::embed::Vector,
        qtokens: &BTreeSet<String>,
        query: &Query,
    ) -> Vec<(NodeId, u32)> {
        let population = u32::try_from(part.nodes.len().max(1)).unwrap_or(u32::MAX);
        let mut overlap: HashMap<&NodeId, u32> = HashMap::new();
        let mut total = 0_u32;
        for token in qtokens {
            let postings = part.index.tokens.get(token);
            let df = postings.map_or(0, |p| u32::try_from(p.len()).unwrap_or(u32::MAX));
            if df > MAX_POSTING {
                continue;
            }
            let idf = 1000_u32
                .saturating_sub(df.saturating_mul(1000).checked_div(population).unwrap_or(0))
                .max(100);
            total = total.saturating_add(idf);
            for id in postings.into_iter().flatten() {
                let slot = overlap.entry(id).or_insert(0);
                *slot = slot.saturating_add(idf);
            }
        }
        let mut out: Vec<(&NodeId, u32)> = Vec::new();
        for node in part.nodes.values() {
            if node.level > ceiling
                || u32::from(node.confidence) < query.min_confidence
                || !(query.kinds.is_empty() || query.kinds.contains(&node.kind))
            {
                continue;
            }
            let semantic = qvec.cosine_permille(&node.vector);
            let hits = overlap.get(&node.id).copied().unwrap_or(0);
            let lexical = hits.saturating_mul(1000).checked_div(total).unwrap_or(0);
            let base = semantic
                .saturating_mul(6)
                .saturating_add(lexical.saturating_mul(4))
                / 10;
            let factor = 400_u32.saturating_add(weight(node).saturating_mul(6) / 10);
            let score = scale(base, factor);
            if score >= self.settings.min_score {
                out.push((&node.id, score));
            }
        }
        let keep = query.limit.saturating_mul(2).max(8);
        if out.len() > keep {
            out.select_nth_unstable_by(keep, |a, b| b.1.cmp(&a.1).then_with(|| a.0.cmp(b.0)));
            out.truncate(keep);
        }
        let out: Vec<(NodeId, u32)> = out.into_iter().map(|(id, s)| (id.clone(), s)).collect();
        out
    }

    fn expand(
        &self,
        part: &Partition,
        ceiling: Level,
        seed: &NodeId,
        score: u32,
        depth: usize,
        found: &mut HashMap<NodeId, (u32, Option<String>)>,
    ) {
        let mut queue: VecDeque<(NodeId, u32, usize)> = VecDeque::new();
        let mut seen: BTreeSet<NodeId> = BTreeSet::new();
        seen.insert(seed.clone());
        queue.push_back((seed.clone(), score, 0));
        let mut budget = MAX_EXPANSION;
        while let Some((id, current, hop)) = queue.pop_front() {
            if hop >= depth || budget == 0 {
                continue;
            }
            for outgoing in [true, false] {
                for edge in part.edges_of(&id, outgoing) {
                    let other = if outgoing { &edge.to } else { &edge.from };
                    let Some(node) = part.nodes.get(other) else {
                        continue;
                    };
                    if edge.status != Status::Active
                        || edge.level > ceiling
                        || node.level > ceiling
                        || !seen.insert(other.clone())
                    {
                        continue;
                    }
                    budget = budget.saturating_sub(1);
                    let next = scale(
                        scale(current, self.settings.expansion_decay),
                        u32::from(edge.confidence),
                    );
                    let slot = found.entry(other.clone()).or_insert((0, None));
                    if next > slot.0 {
                        *slot = (next, Some(edge.relation.clone()));
                    }
                    queue.push_back((other.clone(), next, hop.saturating_add(1)));
                }
            }
        }
    }

    pub fn neighbors(
        &self,
        who: &PersonId,
        query: &NeighborQuery,
    ) -> KnowledgeResult<Vec<Related>> {
        if query.limit == 0 || query.limit > self.settings.max_limit {
            return Err(KnowledgeError::Invalid);
        }
        let part = self.own(who)?;
        let node = query.node.clone().unwrap_or(NodeRef {
            kind: Kind::Person,
            label: crate::model::SELF_KEY.to_owned(),
        });
        if let Some(relation) = &query.relation {
            relation_name(relation)?;
        }
        let key = key_of(&self.settings, node.kind, &node.label)?;
        let id = part
            .find(node.kind, &key)
            .cloned()
            .ok_or(KnowledgeError::NotFound)?;
        let mut out = Vec::new();
        for outgoing in [true, false] {
            let wanted = match query.direction {
                Direction::Out => outgoing,
                Direction::In => !outgoing,
                Direction::Both => true,
            };
            if !wanted {
                continue;
            }
            for edge in part.edges_of(&id, outgoing) {
                let other = if outgoing { &edge.to } else { &edge.from };
                if query.relation.as_ref().is_some_and(|r| *r != edge.relation) {
                    continue;
                }
                let Some(target) = part.nodes.get(other) else {
                    continue;
                };
                let hit = self.hit(part, target, u32::from(edge.confidence), None, query.reveal)?;
                out.push(Related {
                    edge: edge.id.clone(),
                    relation: edge.relation.clone(),
                    outgoing,
                    status: edge.status,
                    confidence: edge.confidence,
                    pinned: edge.pinned,
                    node: hit,
                });
            }
        }
        out.sort_by(|a, b| {
            b.confidence
                .cmp(&a.confidence)
                .then_with(|| a.relation.cmp(&b.relation))
                .then_with(|| a.edge.cmp(&b.edge))
        });
        out.truncate(query.limit);
        Ok(out)
    }

    pub fn path(
        &self,
        who: &PersonId,
        from: &NodeRef,
        to: &NodeRef,
    ) -> KnowledgeResult<Option<Vec<Step>>> {
        let part = self.own(who)?;
        let locate = |r: &NodeRef| -> KnowledgeResult<NodeId> {
            let key = key_of(&self.settings, r.kind, &r.label)?;
            part.find(r.kind, &key)
                .cloned()
                .ok_or(KnowledgeError::NotFound)
        };
        let (start, goal) = (locate(from)?, locate(to)?);
        let mut parent: HashMap<NodeId, (NodeId, String, bool, u32)> = HashMap::new();
        let mut queue = VecDeque::from([(start.clone(), 0_usize)]);
        let mut seen = BTreeSet::from([start.clone()]);
        while let Some((id, hop)) = queue.pop_front() {
            if id == goal {
                break;
            }
            if hop >= self.settings.max_depth.saturating_mul(2) {
                continue;
            }
            for outgoing in [true, false] {
                for edge in part.edges_of(&id, outgoing) {
                    let other = if outgoing { &edge.to } else { &edge.from };
                    if edge.status == Status::Active && seen.insert(other.clone()) {
                        parent.insert(
                            other.clone(),
                            (
                                id.clone(),
                                edge.relation.clone(),
                                outgoing,
                                u32::from(edge.confidence),
                            ),
                        );
                        queue.push_back((other.clone(), hop.saturating_add(1)));
                    }
                }
            }
        }
        if start != goal && !parent.contains_key(&goal) {
            return Ok(None);
        }
        let mut steps = Vec::new();
        let mut cursor = goal;
        while cursor != start {
            let (prev, relation, outgoing, _) = parent
                .get(&cursor)
                .cloned()
                .ok_or(KnowledgeError::Corrupt)?;
            let label = |id: &NodeId| {
                part.nodes
                    .get(id)
                    .map(|n| n.label.clone())
                    .unwrap_or_default()
            };
            steps.push(Step {
                from: label(&prev),
                relation,
                outgoing,
                to: label(&cursor),
            });
            cursor = prev;
        }
        steps.reverse();
        Ok(Some(steps))
    }

    pub fn touch(&mut self, who: &PersonId, ids: &[NodeId], now: u64) {
        let gain = self.settings.reinforce_gain;
        let Some(part) = self.partitions.get_mut(who) else {
            return;
        };
        for id in ids {
            if let Some(node) = part.nodes.get_mut(id) {
                node.uses = node.uses.saturating_add(1);
                node.last_used_ms = now;
                node.salience = to_u16(noisy_or(u32::from(node.salience), gain));
            }
        }
    }
}
