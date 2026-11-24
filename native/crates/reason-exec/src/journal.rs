use std::collections::BTreeMap;

use crate::error::{ExecError, ExecResult};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Record {
    Started,
    Succeeded(String),
    Failed,
}

pub trait Journal {
    fn append(&mut self, key: &str, record: Record) -> ExecResult<()>;
    fn last(&self, key: &str) -> Option<&Record>;
}

#[derive(Debug, Default, Clone)]
pub struct MemoryJournal {
    last: BTreeMap<String, Record>,
    entries: usize,
    limit: usize,
}

impl MemoryJournal {
    #[must_use]
    pub fn new(limit: usize) -> Self {
        Self {
            last: BTreeMap::new(),
            entries: 0,
            limit,
        }
    }

    #[must_use]
    pub fn entries(&self) -> usize {
        self.entries
    }
}

impl Journal for MemoryJournal {
    fn append(&mut self, key: &str, record: Record) -> ExecResult<()> {
        if self.entries >= self.limit {
            return Err(ExecError::Journal("full"));
        }
        self.entries = self.entries.saturating_add(1);
        self.last.insert(key.to_owned(), record);
        Ok(())
    }

    fn last(&self, key: &str) -> Option<&Record> {
        self.last.get(key)
    }
}

#[must_use]
pub fn step_key(plan_hash: &str, step: &str, args: &BTreeMap<String, String>) -> String {
    let mut hasher = blake3::Hasher::new();
    hasher.update(plan_hash.as_bytes());
    hasher.update(&[0]);
    hasher.update(step.as_bytes());
    for (name, value) in args {
        hasher.update(&[0]);
        hasher.update(name.as_bytes());
        hasher.update(&[1]);
        hasher.update(value.as_bytes());
    }
    hasher.finalize().to_hex().to_string()
}
