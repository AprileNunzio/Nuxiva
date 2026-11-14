use nuxiva_context_core::PersonId;
use serde::Serialize;

use crate::error::{KnowledgeError, KnowledgeResult};
use crate::extract::{Fact, MAX_FACTS};
use crate::model::{Evidence, Origin};
use crate::store::Knowledge;
use crate::write::{Change, Link, Spec};

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize)]
pub struct IngestReport {
    pub created: usize,
    pub reinforced: usize,
    pub superseded: usize,
    pub contested: usize,
    pub blocked: usize,
    pub rejected: usize,
}

impl Knowledge {
    pub fn ingest(
        &mut self,
        who: &PersonId,
        facts: &[Fact],
        origin: Origin,
        reference: &str,
        now: u64,
    ) -> KnowledgeResult<IngestReport> {
        if facts.len() > MAX_FACTS.saturating_mul(4) {
            return Err(KnowledgeError::TooLarge);
        }
        if origin == Origin::User {
            return Err(KnowledgeError::Forbidden);
        }
        self.own(who)?;
        let mut report = IngestReport::default();
        for fact in facts {
            let ev = Evidence {
                origin,
                reference: reference.to_owned(),
                confidence: fact.confidence,
            };
            if let Some(detail) = &fact.detail {
                let stored = self.remember(
                    who,
                    &Spec {
                        kind: fact.to.kind,
                        label: &fact.to.label,
                        detail: Some(detail),
                        level: fact.level,
                    },
                    &ev,
                    now,
                );
                match stored {
                    Ok(_) => {}
                    Err(error) if benign(error) => {
                        report.rejected = report.rejected.saturating_add(1);
                        continue;
                    }
                    Err(error) => return Err(error),
                }
            }
            let outcome = self.relate(
                who,
                &Link {
                    from: &fact.from,
                    relation: &fact.relation,
                    to: &fact.to,
                    level: fact.level,
                },
                &ev,
                now,
            );
            match outcome {
                Ok(out) => match out.change {
                    Change::Created => report.created = report.created.saturating_add(1),
                    Change::Reinforced => report.reinforced = report.reinforced.saturating_add(1),
                    Change::Superseded => report.superseded = report.superseded.saturating_add(1),
                    Change::Contested => report.contested = report.contested.saturating_add(1),
                    Change::Blocked => report.blocked = report.blocked.saturating_add(1),
                },
                Err(error) if benign(error) => {
                    report.rejected = report.rejected.saturating_add(1);
                }
                Err(other) => return Err(other),
            }
        }
        Ok(report)
    }
}

fn benign(error: KnowledgeError) -> bool {
    matches!(
        error,
        KnowledgeError::Invalid | KnowledgeError::TooLarge | KnowledgeError::Forbidden
    )
}
