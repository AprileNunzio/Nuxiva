use std::sync::Arc;

use nuxiva_context_core::{Affect, Delta, Lang, PersonId, Request, SharedContext};
use nuxiva_swarm_core::{Ident, Percept};

use crate::error::{PerceptError, PerceptResult};

fn person_id(id: &Ident) -> PerceptResult<PersonId> {
    PersonId::new(id.as_str()).map_err(PerceptError::from)
}

fn present_of(percept: &Percept) -> PerceptResult<Vec<PersonId>> {
    percept.presence.iter().map(person_id).collect()
}

#[derive(Debug, Clone)]
pub struct Fusion {
    context: SharedContext,
}

impl Fusion {
    #[must_use]
    pub fn new(context: SharedContext) -> Self {
        Self { context }
    }

    pub fn apply(&self, percept: &Percept) -> PerceptResult<u64> {
        let mut deltas = vec![Delta::SetPresence {
            present: present_of(percept)?,
            at_ms: percept.at_ms,
        }];
        if let (Some(speaker), Some(emotion)) = (&percept.speaker, &percept.emotion) {
            let person = person_id(speaker)?;
            if self.context.snapshot().person(&person).is_some() {
                deltas.push(Delta::SetAffect {
                    person,
                    affect: Some(Affect {
                        valence: emotion.valence,
                        arousal: emotion.arousal,
                        at_ms: emotion.at_ms,
                    }),
                });
            }
        }
        self.context.apply_all(deltas).map_err(PerceptError::from)
    }

    pub fn request(
        &self,
        percept: &Percept,
        lang: Lang,
        budget_chars: usize,
    ) -> PerceptResult<Request> {
        let subjects = percept
            .speaker
            .as_ref()
            .map(person_id)
            .transpose()?
            .into_iter()
            .collect();
        Ok(Request {
            subjects,
            present: present_of(percept)?,
            lang,
            budget_chars,
            now_ms: percept.at_ms,
        })
    }

    pub fn view(
        &self,
        percept: &Percept,
        lang: Lang,
        budget_chars: usize,
    ) -> PerceptResult<Arc<str>> {
        self.apply(percept)?;
        let request = self.request(percept, lang, budget_chars)?;
        Ok(self.context.render(&request))
    }
}
