use nuxiva_context_core::PersonId;
use serde::{Deserialize, Serialize};

use crate::error::{KnowledgeError, KnowledgeResult};
use crate::model::{Edge, EdgeId, Evidence, Level, NodeId, NodeRef, Origin, SELF_KEY, Status};
use crate::store::{Knowledge, composite};
use crate::text::{clean, relation_name};
use crate::write::{
    Change, Ctx, Link, Outcome, Spec, ensure_node, evidence, key_of, push_provenance, reseal,
    set_detail,
};

const MAX_BLOCKED: usize = 10_000;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case", tag = "action", deny_unknown_fields)]
pub enum Correction {
    Assert {
        from: NodeRef,
        relation: String,
        to: NodeRef,
        #[serde(default = "private")]
        level: Level,
    },
    Refute {
        from: NodeRef,
        relation: String,
        to: NodeRef,
    },
    Rename {
        node: NodeRef,
        label: String,
    },
    Remove {
        node: NodeRef,
    },
    Restrict {
        node: NodeRef,
        level: Level,
    },
    SetDetail {
        node: NodeRef,
        detail: Option<String>,
    },
}

const fn private() -> Level {
    Level::Private
}

fn user_evidence() -> Evidence {
    Evidence {
        origin: Origin::User,
        reference: "correction".to_owned(),
        confidence: 1000,
    }
}

impl Knowledge {
    pub fn correct(
        &mut self,
        who: &PersonId,
        correction: &Correction,
        now: u64,
    ) -> KnowledgeResult<Outcome> {
        match correction {
            Correction::Assert {
                from,
                relation,
                to,
                level,
            } => self.relate(
                who,
                &Link {
                    from,
                    relation,
                    to,
                    level: *level,
                },
                &user_evidence(),
                now,
            ),
            Correction::Refute { from, relation, to } => self.refute(who, from, relation, to, now),
            Correction::Rename { node, label } => self.rename(who, node, label, now),
            Correction::Remove { node } => self.remove(who, node),
            Correction::Restrict { node, level } => self.restrict(who, node, *level, now),
            Correction::SetDetail { node, detail } => {
                self.set_node_detail(who, node, detail.as_deref(), now)
            }
        }
    }

    fn locate(&self, who: &PersonId, node: &NodeRef) -> KnowledgeResult<NodeId> {
        let key = key_of(&self.settings, node.kind, &node.label)?;
        self.own(who)?
            .find(node.kind, &key)
            .cloned()
            .ok_or(KnowledgeError::NotFound)
    }

    fn refute(
        &mut self,
        who: &PersonId,
        from: &NodeRef,
        relation: &str,
        to: &NodeRef,
        now: u64,
    ) -> KnowledgeResult<Outcome> {
        relation_name(relation)?;
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
        let ev = user_evidence();
        let spec = |r: &NodeRef| (r.kind, r.label.clone());
        let (fk, fl) = spec(from);
        let (tk, tl) = spec(to);
        let from_id = ensure_node(
            &ctx,
            part,
            &Spec {
                kind: fk,
                label: &fl,
                detail: None,
                level: Level::Private,
            },
            &ev,
        )?;
        let to_id = ensure_node(
            &ctx,
            part,
            &Spec {
                kind: tk,
                label: &tl,
                detail: None,
                level: Level::Private,
            },
            &ev,
        )?;
        let id = EdgeId::derive(&from_id, relation, &to_id);
        let (_, provenance) = evidence(&ev, now)?;
        if let Some(edge) = part.edges.get_mut(&id) {
            edge.status = Status::Refuted;
            edge.confidence = 0;
            edge.pinned = true;
            edge.updated_ms = now;
            push_provenance(&mut edge.provenance, provenance, settings.max_provenance);
        } else {
            part.edges.insert(
                id.clone(),
                Edge {
                    id: id.clone(),
                    from: from_id.clone(),
                    to: to_id.clone(),
                    relation: relation.to_owned(),
                    level: Level::Private,
                    status: Status::Refuted,
                    confidence: 0,
                    salience: 1000,
                    pinned: true,
                    created_ms: now,
                    updated_ms: now,
                    last_used_ms: now,
                    provenance: vec![provenance],
                },
            );
            part.link(id.clone(), from_id, to_id);
        }
        Ok(Outcome {
            id,
            change: Change::Superseded,
        })
    }

    fn rename(
        &mut self,
        who: &PersonId,
        node: &NodeRef,
        label: &str,
        now: u64,
    ) -> KnowledgeResult<Outcome> {
        let id = self.locate(who, node)?;
        let max = self.settings.max_label_chars;
        let new_label = clean(label, max)?;
        let new_key = key_of(&self.settings, node.kind, &new_label)?;
        let part = self.own_mut(who)?;
        let old_key = part
            .nodes
            .get(&id)
            .ok_or(KnowledgeError::NotFound)?
            .key
            .clone();
        if old_key == SELF_KEY {
            return Err(KnowledgeError::Forbidden);
        }
        if part
            .find(node.kind, &new_key)
            .is_some_and(|other| *other != id)
        {
            return Err(KnowledgeError::Invalid);
        }
        part.unindex_tokens(&id);
        part.index.keys.remove(&composite(node.kind, &old_key));
        let item = part.nodes.get_mut(&id).ok_or(KnowledgeError::Corrupt)?;
        item.label = new_label;
        item.key = new_key;
        item.pinned = true;
        item.updated_ms = now;
        part.refresh(&id);
        Ok(Outcome {
            id: EdgeId(id.0),
            change: Change::Reinforced,
        })
    }

    fn remove(&mut self, who: &PersonId, node: &NodeRef) -> KnowledgeResult<Outcome> {
        let id = self.locate(who, node)?;
        let part = self.own_mut(who)?;
        let target = part.nodes.get(&id).ok_or(KnowledgeError::NotFound)?;
        if target.key == SELF_KEY {
            return Err(KnowledgeError::Forbidden);
        }
        if part.blocked.len() >= MAX_BLOCKED {
            return Err(KnowledgeError::Capacity);
        }
        part.blocked.insert(composite(target.kind, &target.key));
        part.drop_node(&id);
        Ok(Outcome {
            id: EdgeId(id.0),
            change: Change::Superseded,
        })
    }

    fn restrict(
        &mut self,
        who: &PersonId,
        node: &NodeRef,
        level: Level,
        now: u64,
    ) -> KnowledgeResult<Outcome> {
        let id = self.locate(who, node)?;
        let Self {
            key, partitions, ..
        } = self;
        let part = partitions.get_mut(who).ok_or(KnowledgeError::NotFound)?;
        let owner = part.owner.clone();
        let item = part.nodes.get_mut(&id).ok_or(KnowledgeError::NotFound)?;
        item.level = level;
        item.pinned = true;
        item.updated_ms = now;
        reseal(key.as_deref(), &owner, item)?;
        let touched: Vec<EdgeId> = [true, false]
            .iter()
            .flat_map(|out| part.edges_of(&id, *out).map(|e| e.id.clone()))
            .collect();
        for edge in touched {
            if let Some(e) = part.edges.get_mut(&edge) {
                e.level = e.level.max(level);
            }
        }
        part.refresh(&id);
        Ok(Outcome {
            id: EdgeId(id.0),
            change: Change::Reinforced,
        })
    }

    fn set_node_detail(
        &mut self,
        who: &PersonId,
        node: &NodeRef,
        detail: Option<&str>,
        now: u64,
    ) -> KnowledgeResult<Outcome> {
        let id = self.locate(who, node)?;
        let max = self.settings.max_detail_chars;
        let text = detail.map(|d| clean(d, max)).transpose()?;
        let Self {
            key, partitions, ..
        } = self;
        let part = partitions.get_mut(who).ok_or(KnowledgeError::NotFound)?;
        let owner = part.owner.clone();
        let item = part.nodes.get_mut(&id).ok_or(KnowledgeError::NotFound)?;
        set_detail(key.as_deref(), &owner, item, text.as_deref())?;
        item.pinned = true;
        item.updated_ms = now;
        part.refresh(&id);
        Ok(Outcome {
            id: EdgeId(id.0),
            change: Change::Reinforced,
        })
    }
}
