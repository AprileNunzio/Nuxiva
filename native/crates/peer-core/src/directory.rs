use crate::addr::check_addrs;
use crate::envelope::{Envelope, Verifier};
use crate::error::{PeerError, PeerResult};
use crate::message::Message;
use crate::registry::MAX_NODES;
use std::collections::BTreeMap;

pub const MAX_DIFF: usize = 64;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Record {
    pub seq: u64,
    pub addrs: Vec<String>,
    pub learned_at: i64,
    pub envelope: Envelope,
}

#[derive(Debug, Clone, Default)]
pub struct Directory {
    records: BTreeMap<String, Record>,
    failures: BTreeMap<(String, String), u32>,
}

impl Directory {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn learn(
        &mut self,
        verifier: &Verifier,
        envelope: &Envelope,
        now: i64,
    ) -> PeerResult<bool> {
        let message = verifier.verify_signature(envelope)?;
        let Message::Locate { addrs } = message else {
            return Err(PeerError::Payload);
        };
        check_addrs(&addrs)?;
        if let Some(current) = self.records.get(&envelope.from) {
            if envelope.seq <= current.seq {
                return Ok(false);
            }
        } else if self.records.len() >= MAX_NODES {
            return Err(PeerError::Capacity);
        }
        self.failures.retain(|(id, _), _| id != &envelope.from);
        self.records.insert(
            envelope.from.clone(),
            Record {
                seq: envelope.seq,
                addrs,
                learned_at: now,
                envelope: envelope.clone(),
            },
        );
        Ok(true)
    }

    #[must_use]
    pub fn get(&self, id: &str) -> Option<&Record> {
        self.records.get(id)
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.records.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.records.is_empty()
    }

    #[must_use]
    pub fn candidates(&self, id: &str) -> Vec<String> {
        let Some(record) = self.records.get(id) else {
            return Vec::new();
        };
        let mut addrs: Vec<(u32, usize, &String)> = record
            .addrs
            .iter()
            .enumerate()
            .map(|(i, a)| {
                let fails = self
                    .failures
                    .get(&(id.to_owned(), a.clone()))
                    .copied()
                    .unwrap_or(0);
                (fails, i, a)
            })
            .collect();
        addrs.sort();
        addrs.into_iter().map(|(_, _, a)| a.clone()).collect()
    }

    pub fn report_failure(&mut self, id: &str, addr: &str) {
        let slot = self
            .failures
            .entry((id.to_owned(), addr.to_owned()))
            .or_default();
        *slot = slot.saturating_add(1);
    }

    pub fn report_success(&mut self, id: &str, addr: &str) {
        self.failures.remove(&(id.to_owned(), addr.to_owned()));
    }

    #[must_use]
    pub fn digest(&self) -> Vec<(String, u64)> {
        self.records
            .iter()
            .map(|(id, r)| (id.clone(), r.seq))
            .collect()
    }

    #[must_use]
    pub fn newer_than(&self, remote: &[(String, u64)]) -> Vec<Envelope> {
        let known: BTreeMap<&str, u64> =
            remote.iter().map(|(id, seq)| (id.as_str(), *seq)).collect();
        self.records
            .iter()
            .filter(|(id, r)| known.get(id.as_str()).is_none_or(|seq| r.seq > *seq))
            .map(|(_, r)| r.envelope.clone())
            .take(MAX_DIFF)
            .collect()
    }

    pub fn forget(&mut self, id: &str) {
        self.records.remove(id);
        self.failures.retain(|(node, _), _| node != id);
    }
}
