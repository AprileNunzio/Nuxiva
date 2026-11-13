use crate::id::PersonId;
use crate::model::{Affect, Person};

#[derive(Debug, Clone)]
pub enum Delta {
    Upsert(Box<Person>),
    Remove(PersonId),
    SetAffect {
        person: PersonId,
        affect: Option<Affect>,
    },
    SetPresence {
        present: Vec<PersonId>,
        at_ms: u64,
    },
    MarkStale {
        person: PersonId,
        stale: bool,
    },
}
