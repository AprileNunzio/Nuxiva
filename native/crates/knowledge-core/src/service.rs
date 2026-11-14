use std::sync::{Arc, PoisonError, RwLock};

use nuxiva_context_core::PersonId;
use serde_json::{Value, json};

use crate::error::{KnowledgeError, KnowledgeResult};
use crate::extract::Extractor;
use crate::model::{Evidence, Kind, NodeRef, Origin};
use crate::seal::MasterKey;
use crate::settings::KnowledgeSettings;
use crate::store::Knowledge;
use crate::vault::Vault;
use crate::wire::{Command, MAX_REQUEST};
use crate::write::{Link, Spec};

pub type Clock = Arc<dyn Fn() -> u64 + Send + Sync>;

pub struct Service {
    inner: RwLock<Knowledge>,
    vault: Option<Vault>,
    extractor: Extractor,
    clock: Clock,
    autosave: bool,
}

impl std::fmt::Debug for Service {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Service(..)")
    }
}

#[must_use]
pub fn system_clock() -> Clock {
    Arc::new(|| {
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .ok()
            .and_then(|d| u64::try_from(d.as_millis()).ok())
            .unwrap_or(0)
    })
}

fn to_value<T: serde::Serialize>(value: &T) -> KnowledgeResult<Value> {
    serde_json::to_value(value).map_err(|_| KnowledgeError::Corrupt)
}

fn user_origin_barred(origin: Origin) -> KnowledgeResult<()> {
    if origin == Origin::User {
        Err(KnowledgeError::Forbidden)
    } else {
        Ok(())
    }
}

impl Service {
    pub fn new(
        settings: KnowledgeSettings,
        key: Option<Arc<MasterKey>>,
        vault: Option<Vault>,
        clock: Clock,
        autosave: bool,
    ) -> KnowledgeResult<Self> {
        Ok(Self {
            inner: RwLock::new(Knowledge::new(settings, key)?),
            vault,
            extractor: Extractor::new()?,
            clock,
            autosave,
        })
    }

    #[must_use]
    pub fn handle(&self, raw: &str) -> String {
        let result = if raw.len() > MAX_REQUEST {
            Err(KnowledgeError::TooLarge)
        } else {
            serde_json::from_str::<Command>(raw)
                .map_err(|_| KnowledgeError::Invalid)
                .and_then(|command| self.execute(command))
        };
        let envelope = match result {
            Ok(data) => json!({"ok": true, "data": data}),
            Err(error) => json!({"ok": false, "error": error.code()}),
        };
        envelope.to_string()
    }

    fn save(&self, who: &PersonId) -> KnowledgeResult<()> {
        let Some(vault) = &self.vault else {
            return Ok(());
        };
        let guard = self.inner.read().unwrap_or_else(PoisonError::into_inner);
        vault.save(guard.partition(who)?)
    }

    fn autosaved(&self, who: &PersonId, value: Value) -> KnowledgeResult<Value> {
        if self.autosave {
            self.save(who)?;
        }
        Ok(value)
    }

    #[allow(clippy::too_many_lines)]
    fn execute(&self, command: Command) -> KnowledgeResult<Value> {
        let now = (self.clock)();
        match command {
            Command::Register {
                id,
                name,
                role,
                consent,
            } => {
                let mut kn = self.inner.write().unwrap_or_else(PoisonError::into_inner);
                kn.register(&id, &name, role, consent)?;
                drop(kn);
                self.autosaved(&id, json!({"registered": true}))
            }
            Command::Remember {
                who,
                kind,
                label,
                detail,
                level,
                confidence,
                origin,
                reference,
            } => {
                user_origin_barred(origin)?;
                let ev = Evidence {
                    origin,
                    reference,
                    confidence,
                };
                let id = self
                    .inner
                    .write()
                    .unwrap_or_else(PoisonError::into_inner)
                    .remember(
                        &who,
                        &Spec {
                            kind,
                            label: &label,
                            detail: detail.as_deref(),
                            level,
                        },
                        &ev,
                        now,
                    )?;
                self.autosaved(&who, json!({"id": id}))
            }
            Command::Relate {
                who,
                from,
                relation,
                to,
                level,
                confidence,
                origin,
                reference,
            } => {
                user_origin_barred(origin)?;
                let ev = Evidence {
                    origin,
                    reference,
                    confidence,
                };
                let outcome = self
                    .inner
                    .write()
                    .unwrap_or_else(PoisonError::into_inner)
                    .relate(
                        &who,
                        &Link {
                            from: &from,
                            relation: &relation,
                            to: &to,
                            level,
                        },
                        &ev,
                        now,
                    )?;
                self.autosaved(
                    &who,
                    json!({"edge": outcome.id, "change": outcome.change.name()}),
                )
            }
            Command::Correct { who, correction } => {
                let outcome = self
                    .inner
                    .write()
                    .unwrap_or_else(PoisonError::into_inner)
                    .correct(&who, &correction, now)?;
                self.autosaved(
                    &who,
                    json!({"id": outcome.id, "change": outcome.change.name()}),
                )
            }
            Command::Search { who, query } => {
                let hits = self
                    .inner
                    .read()
                    .unwrap_or_else(PoisonError::into_inner)
                    .search(&who, &query)?;
                let own: Vec<_> = hits
                    .iter()
                    .filter(|h| h.owner == who)
                    .map(|h| h.id.clone())
                    .collect();
                self.inner
                    .write()
                    .unwrap_or_else(PoisonError::into_inner)
                    .touch(&who, &own, now);
                to_value(&hits)
            }
            Command::Neighbors { who, query } => to_value(
                &self
                    .inner
                    .read()
                    .unwrap_or_else(PoisonError::into_inner)
                    .neighbors(&who, &query)?,
            ),
            Command::Path { who, from, to } => to_value(
                &self
                    .inner
                    .read()
                    .unwrap_or_else(PoisonError::into_inner)
                    .path(&who, &from, &to)?,
            ),
            Command::Extract {
                who,
                text,
                origin,
                reference,
                store,
            } => {
                user_origin_barred(origin)?;
                let facts = self.extractor.extract(&text)?;
                if !store {
                    return to_value(&facts);
                }
                let report = self
                    .inner
                    .write()
                    .unwrap_or_else(PoisonError::into_inner)
                    .ingest(&who, &facts, origin, &reference, now)?;
                self.autosaved(&who, json!({"facts": facts, "report": report}))
            }
            Command::Ingest {
                who,
                facts,
                origin,
                reference,
            } => {
                let report = self
                    .inner
                    .write()
                    .unwrap_or_else(PoisonError::into_inner)
                    .ingest(&who, &facts, origin, &reference, now)?;
                self.autosaved(&who, to_value(&report)?)
            }
            Command::Observe { who, label } => {
                let habit = self
                    .inner
                    .write()
                    .unwrap_or_else(PoisonError::into_inner)
                    .observe(&who, &label, now)?;
                self.autosaved(&who, json!({"habit": habit}))
            }
            Command::Consolidate { who } => {
                let report = self
                    .inner
                    .write()
                    .unwrap_or_else(PoisonError::into_inner)
                    .consolidate(&who, now)?;
                self.autosaved(&who, to_value(&report)?)
            }
            Command::Export { who } => to_value(
                &self
                    .inner
                    .read()
                    .unwrap_or_else(PoisonError::into_inner)
                    .export(&who)?,
            ),
            Command::Erase { who, confirm } => {
                let receipt = self
                    .inner
                    .write()
                    .unwrap_or_else(PoisonError::into_inner)
                    .erase(&who, &confirm)?;
                let file = match &self.vault {
                    Some(vault) => vault.delete(&who)?,
                    None => false,
                };
                Ok(json!({"receipt": receipt, "file_removed": file}))
            }
            Command::Stats { who } => self.stats(&who),
            Command::Persist { who } => {
                self.save(&who)?;
                Ok(json!({"saved": self.vault.is_some()}))
            }
            Command::Restore { id } => {
                let vault = self.vault.as_ref().ok_or(KnowledgeError::NotFound)?;
                let part = vault.load(&id)?.ok_or(KnowledgeError::NotFound)?;
                self.inner
                    .write()
                    .unwrap_or_else(PoisonError::into_inner)
                    .install(part)?;
                Ok(json!({"restored": true}))
            }
        }
    }

    fn stats(&self, who: &PersonId) -> KnowledgeResult<Value> {
        let guard = self.inner.read().unwrap_or_else(PoisonError::into_inner);
        let part = guard.own(who)?;
        let by_kind: Vec<Value> = Kind::ALL
            .iter()
            .map(|k| {
                let n = part.nodes.values().filter(|n| n.kind == *k).count();
                json!({"kind": k.name(), "nodes": n})
            })
            .collect();
        let _ = NodeRef {
            kind: Kind::Person,
            label: String::new(),
        };
        Ok(json!({
            "nodes": part.nodes.len(),
            "edges": part.edges.len(),
            "pinned": part.nodes.values().filter(|n| n.pinned).count(),
            "by_kind": by_kind,
            "observations": part.observations.len(),
        }))
    }
}
