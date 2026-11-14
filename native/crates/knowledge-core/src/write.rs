use nuxiva_context_core::PersonId;

use crate::error::{KnowledgeError, KnowledgeResult};
use crate::model::{
    Detail, Edge, EdgeId, Evidence, Kind, Level, Node, NodeId, NodeRef, Origin, Provenance,
    SELF_KEY, Status,
};
use crate::num::{clamp, noisy_or, to_u16};
use crate::seal::MasterKey;
use crate::settings::KnowledgeSettings;
use crate::store::{Knowledge, Partition, composite};
use crate::text::{clean, normalize, relation_name};

pub const INITIAL_SALIENCE: u32 = 700;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Change {
    Created,
    Reinforced,
    Superseded,
    Contested,
    Blocked,
}

impl Change {
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Created => "created",
            Self::Reinforced => "reinforced",
            Self::Superseded => "superseded",
            Self::Contested => "contested",
            Self::Blocked => "blocked",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Outcome {
    pub id: EdgeId,
    pub change: Change,
}

pub fn evidence(ev: &Evidence, now: u64) -> KnowledgeResult<(u32, Provenance)> {
    let reference = if ev.reference.is_empty() {
        String::new()
    } else {
        clean(&ev.reference, 128)?
    };
    Ok((
        ev.confidence.min(ev.origin.cap()),
        Provenance {
            origin: ev.origin,
            reference,
            at_ms: now,
        },
    ))
}

pub fn push_provenance(list: &mut Vec<Provenance>, item: Provenance, max: usize) {
    list.push(item);
    while list.len() > max {
        let victim = list
            .iter()
            .position(|p| p.origin != Origin::User)
            .unwrap_or(0);
        list.remove(victim);
    }
}

pub fn detail_aad(owner: &PersonId, id: &NodeId) -> Vec<u8> {
    format!("nuxiva.knowledge.detail.v1|{}|{}", owner.as_str(), id.0).into_bytes()
}

pub fn set_detail(
    key: Option<&MasterKey>,
    owner: &PersonId,
    node: &mut Node,
    text: Option<&str>,
) -> KnowledgeResult<()> {
    node.detail = match text {
        None => None,
        Some(t) if node.level == Level::Secret => {
            let key = key.ok_or(KnowledgeError::Seal)?;
            let aad = detail_aad(owner, &node.id);
            let (nonce, data) = key.owner(owner.as_str())?.seal(&aad, t.as_bytes())?;
            Some(Detail::Sealed { nonce, data })
        }
        Some(t) => Some(Detail::Plain { text: t.to_owned() }),
    };
    Ok(())
}

pub fn read_detail(
    key: Option<&MasterKey>,
    owner: &PersonId,
    node: &Node,
) -> KnowledgeResult<Option<String>> {
    match &node.detail {
        None => Ok(None),
        Some(Detail::Plain { text }) => Ok(Some(text.clone())),
        Some(Detail::Sealed { nonce, data }) => {
            let key = key.ok_or(KnowledgeError::Seal)?;
            let plain =
                key.owner(owner.as_str())?
                    .open(&detail_aad(owner, &node.id), nonce, data)?;
            String::from_utf8(plain.to_vec())
                .map(Some)
                .map_err(|_| KnowledgeError::Seal)
        }
    }
}

pub fn reseal(
    master: Option<&MasterKey>,
    owner: &PersonId,
    node: &mut Node,
) -> KnowledgeResult<()> {
    let sealed = matches!(node.detail, Some(Detail::Sealed { .. }));
    if sealed == (node.level == Level::Secret) {
        return Ok(());
    }
    let plain = read_detail(master, owner, node)?;
    set_detail(master, owner, node, plain.as_deref())
}

pub struct Spec<'a> {
    pub kind: Kind,
    pub label: &'a str,
    pub detail: Option<&'a str>,
    pub level: Level,
}

pub fn key_of(settings: &KnowledgeSettings, kind: Kind, label: &str) -> KnowledgeResult<String> {
    if label == SELF_KEY {
        return if kind == Kind::Person {
            Ok(SELF_KEY.to_owned())
        } else {
            Err(KnowledgeError::Invalid)
        };
    }
    let label = clean(label, settings.max_label_chars)?;
    let key = normalize(&label);
    if key.is_empty() || label.starts_with('@') {
        return Err(KnowledgeError::Invalid);
    }
    Ok(key)
}

pub struct Ctx<'a> {
    pub settings: &'a KnowledgeSettings,
    pub master: Option<&'a MasterKey>,
    pub total_nodes: usize,
    pub now: u64,
}

pub fn ensure_node(
    ctx: &Ctx<'_>,
    part: &mut Partition,
    spec: &Spec<'_>,
    ev: &Evidence,
) -> KnowledgeResult<NodeId> {
    let settings = ctx.settings;
    let now = ctx.now;
    let (confidence, provenance) = evidence(ev, now)?;
    let key = key_of(settings, spec.kind, spec.label)?;
    let detail = spec
        .detail
        .map(|d| clean(d, settings.max_detail_chars))
        .transpose()?;
    let user = ev.origin == Origin::User;
    if !user && part.blocked.contains(&composite(spec.kind, &key)) {
        return Err(KnowledgeError::Forbidden);
    }
    let owner = part.owner.clone();
    let id = if let Some(id) = part.find(spec.kind, &key).cloned() {
        let node = part.nodes.get_mut(&id).ok_or(KnowledgeError::Corrupt)?;
        node.confidence = to_u16(noisy_or(u32::from(node.confidence), confidence));
        node.salience = to_u16(noisy_or(u32::from(node.salience), settings.reinforce_gain));
        node.level = if user {
            spec.level
        } else {
            node.level.max(spec.level)
        };
        let locked = node.pinned && !user;
        node.pinned |= user;
        node.updated_ms = now;
        push_provenance(&mut node.provenance, provenance, settings.max_provenance);
        match (&detail, locked) {
            (Some(text), false) => set_detail(ctx.master, &owner, node, Some(text))?,
            _ => reseal(ctx.master, &owner, node)?,
        }
        id
    } else {
        if ctx.total_nodes >= settings.max_nodes || part.nodes.len() >= settings.max_nodes {
            return Err(KnowledgeError::Capacity);
        }
        part.blocked.remove(&composite(spec.kind, &key));
        let id = NodeId::derive(spec.kind, &key);
        let label = if key == SELF_KEY {
            part.name.clone()
        } else {
            clean(spec.label, settings.max_label_chars)?
        };
        let mut node = Node {
            id: id.clone(),
            kind: spec.kind,
            key,
            label,
            detail: None,
            level: spec.level,
            confidence: to_u16(clamp(confidence)),
            salience: to_u16(if user { 1000 } else { INITIAL_SALIENCE }),
            pinned: user,
            created_ms: now,
            updated_ms: now,
            last_used_ms: now,
            uses: 0,
            provenance: vec![provenance],
            vector: crate::embed::Vector::default(),
        };
        set_detail(ctx.master, &owner, &mut node, detail.as_deref())?;
        part.nodes.insert(id.clone(), node);
        id
    };
    part.refresh(&id);
    Ok(id)
}

impl std::fmt::Debug for Spec<'_> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Spec(..)")
    }
}

impl std::fmt::Debug for Link<'_> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Link(..)")
    }
}

pub struct Link<'a> {
    pub from: &'a NodeRef,
    pub relation: &'a str,
    pub to: &'a NodeRef,
    pub level: Level,
}

fn blocked(id: EdgeId) -> Outcome {
    Outcome {
        id,
        change: Change::Blocked,
    }
}

impl Knowledge {
    pub fn remember(
        &mut self,
        who: &PersonId,
        spec: &Spec<'_>,
        ev: &Evidence,
        now: u64,
    ) -> KnowledgeResult<NodeId> {
        let total_nodes = self.total_nodes();
        let Self {
            settings,
            key,
            partitions,
        } = self;
        let part = partitions.get_mut(who).ok_or(KnowledgeError::NotFound)?;
        if !part.consent {
            return Err(KnowledgeError::Forbidden);
        }
        let ctx = Ctx {
            settings,
            master: key.as_deref(),
            total_nodes,
            now,
        };
        ensure_node(&ctx, part, spec, ev)
    }

    pub fn relate(
        &mut self,
        who: &PersonId,
        link: &Link<'_>,
        ev: &Evidence,
        now: u64,
    ) -> KnowledgeResult<Outcome> {
        relation_name(link.relation)?;
        let total_nodes = self.total_nodes();
        let total_edges = self.total_edges();
        let Self {
            settings,
            key,
            partitions,
        } = self;
        let part = partitions.get_mut(who).ok_or(KnowledgeError::NotFound)?;
        if !part.consent {
            return Err(KnowledgeError::Forbidden);
        }
        let ctx = Ctx {
            settings,
            master: key.as_deref(),
            total_nodes,
            now,
        };
        let (confidence, provenance) = evidence(ev, now)?;
        let user = ev.origin == Origin::User;
        let from_id = ensure_node(
            &ctx,
            part,
            &Spec {
                kind: link.from.kind,
                label: &link.from.label,
                detail: None,
                level: link.level,
            },
            ev,
        )?;
        let to_key = key_of(settings, link.to.kind, &link.to.label)?;
        let to_id = NodeId::derive(link.to.kind, &to_key);
        let edge_id = EdgeId::derive(&from_id, link.relation, &to_id);
        let current = part.edges.get(&edge_id).map(|e| e.status);
        if current == Some(Status::Refuted) && !user {
            return Ok(blocked(edge_id));
        }
        let superseded = match rival_gate(
            settings,
            part,
            &from_id,
            link.relation,
            &to_id,
            (user, confidence),
            now,
        ) {
            Gate::Stop(change) => {
                return Ok(Outcome {
                    id: edge_id,
                    change,
                });
            }
            Gate::Go(superseded) => superseded,
        };
        if current.is_none() && total_edges >= settings.max_edges {
            return Err(KnowledgeError::Capacity);
        }
        let to_id = ensure_node(
            &ctx,
            part,
            &Spec {
                kind: link.to.kind,
                label: &link.to.label,
                detail: None,
                level: link.level,
            },
            ev,
        )?;
        let floor = [&from_id, &to_id]
            .iter()
            .filter_map(|id| part.nodes.get(*id))
            .map(|n| n.level)
            .fold(link.level, Level::max);
        let ends = Ends {
            id: &edge_id,
            from: &from_id,
            to: &to_id,
            relation: link.relation,
            level: floor,
        };
        let change = apply_edge(settings, part, &ends, (confidence, provenance), user, now);
        Ok(Outcome {
            id: edge_id,
            change: if superseded && change == Change::Created {
                Change::Superseded
            } else {
                change
            },
        })
    }
}

enum Gate {
    Stop(Change),
    Go(bool),
}

fn rival_gate(
    settings: &KnowledgeSettings,
    part: &mut Partition,
    from_id: &NodeId,
    relation: &str,
    to_id: &NodeId,
    stance: (bool, u32),
    now: u64,
) -> Gate {
    if !settings.is_functional(relation) {
        return Gate::Go(false);
    }
    let (user, confidence) = stance;
    let rivals: Vec<EdgeId> = part
        .edges_of(from_id, true)
        .filter(|e| e.relation == relation && e.to != *to_id && e.status == Status::Active)
        .map(|e| e.id.clone())
        .collect();
    if !user {
        let strongest = rivals
            .iter()
            .filter_map(|id| part.edges.get(id))
            .map(|e| (e.pinned, u32::from(e.confidence)))
            .max();
        match strongest {
            Some((true, _)) => return Gate::Stop(Change::Blocked),
            Some((false, c)) if confidence < c => return Gate::Stop(Change::Contested),
            _ => {}
        }
    }
    let mut superseded = false;
    for id in &rivals {
        if let Some(edge) = part.edges.get_mut(id) {
            edge.status = Status::Superseded;
            edge.pinned = false;
            edge.updated_ms = now;
            superseded = true;
        }
    }
    Gate::Go(superseded)
}

struct Ends<'a> {
    id: &'a EdgeId,
    from: &'a NodeId,
    to: &'a NodeId,
    relation: &'a str,
    level: Level,
}

fn apply_edge(
    settings: &KnowledgeSettings,
    part: &mut Partition,
    ends: &Ends<'_>,
    evidence: (u32, Provenance),
    user: bool,
    now: u64,
) -> Change {
    let (confidence, provenance) = evidence;
    if let Some(edge) = part.edges.get_mut(ends.id) {
        let reactivated = edge.status != Status::Active;
        edge.status = Status::Active;
        edge.confidence = if user || reactivated {
            to_u16(confidence)
        } else {
            to_u16(noisy_or(u32::from(edge.confidence), confidence))
        };
        edge.salience = to_u16(noisy_or(u32::from(edge.salience), settings.reinforce_gain));
        edge.level = if user {
            ends.level
        } else {
            edge.level.max(ends.level)
        };
        edge.pinned |= user;
        edge.updated_ms = now;
        push_provenance(&mut edge.provenance, provenance, settings.max_provenance);
        return if reactivated {
            Change::Created
        } else {
            Change::Reinforced
        };
    }
    let edge = Edge {
        id: ends.id.clone(),
        from: ends.from.clone(),
        to: ends.to.clone(),
        relation: ends.relation.to_owned(),
        level: ends.level,
        status: Status::Active,
        confidence: to_u16(confidence),
        salience: to_u16(if user { 1000 } else { INITIAL_SALIENCE }),
        pinned: user,
        created_ms: now,
        updated_ms: now,
        last_used_ms: now,
        provenance: vec![provenance],
    };
    part.edges.insert(ends.id.clone(), edge);
    part.link(ends.id.clone(), ends.from.clone(), ends.to.clone());
    Change::Created
}
