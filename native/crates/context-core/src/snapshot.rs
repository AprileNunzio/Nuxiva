use std::collections::BTreeMap;
use std::sync::Arc;

use crate::delta::Delta;
use crate::error::{ContextError, ContextResult};
use crate::id::PersonId;
use crate::model::Person;
use crate::settings::ContextSettings;

#[derive(Debug, Clone, Default)]
pub struct Snapshot {
    version: u64,
    persons: BTreeMap<PersonId, Arc<Person>>,
    present: Vec<PersonId>,
    present_at_ms: u64,
}

impl Snapshot {
    #[must_use]
    pub fn version(&self) -> u64 {
        self.version
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.persons.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.persons.is_empty()
    }

    #[must_use]
    pub fn person(&self, id: &PersonId) -> Option<&Arc<Person>> {
        self.persons.get(id)
    }

    pub fn persons(&self) -> impl Iterator<Item = &Arc<Person>> {
        self.persons.values()
    }

    #[must_use]
    pub fn present(&self) -> &[PersonId] {
        &self.present
    }

    #[must_use]
    pub fn present_at_ms(&self) -> u64 {
        self.present_at_ms
    }

    pub fn apply(&self, delta: Delta, settings: &ContextSettings) -> ContextResult<Self> {
        let mut next = self.clone();
        next.version = self.version.saturating_add(1);
        match delta {
            Delta::Upsert(person) => {
                person.validate(settings)?;
                if !next.persons.contains_key(&person.id)
                    && next.persons.len() >= settings.max_persons
                {
                    return Err(ContextError::Capacity);
                }
                next.persons.insert(person.id.clone(), Arc::new(*person));
            }
            Delta::Remove(id) => {
                if next.persons.remove(&id).is_none() {
                    return Err(ContextError::Unknown);
                }
                next.present.retain(|p| p != &id);
            }
            Delta::SetAffect { person, affect } => {
                let mut updated = next
                    .persons
                    .get(&person)
                    .map(|p| (**p).clone())
                    .ok_or(ContextError::Unknown)?;
                updated.affect = affect;
                updated.validate(settings)?;
                next.persons.insert(person, Arc::new(updated));
            }
            Delta::SetPresence { present, at_ms } => {
                if present.len() > settings.max_list_items {
                    return Err(ContextError::TooLarge);
                }
                let mut unique: Vec<PersonId> = Vec::with_capacity(present.len());
                for id in present {
                    if !unique.contains(&id) {
                        unique.push(id);
                    }
                }
                next.present = unique;
                next.present_at_ms = at_ms;
            }
            Delta::MarkStale { person, stale } => {
                let mut updated = next
                    .persons
                    .get(&person)
                    .map(|p| (**p).clone())
                    .ok_or(ContextError::Unknown)?;
                updated.stale = stale;
                next.persons.insert(person, Arc::new(updated));
            }
        }
        Ok(next)
    }
}
