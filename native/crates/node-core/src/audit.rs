use crate::hexutil;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

pub const GENESIS: &str = "0000000000000000000000000000000000000000000000000000000000000000";
const MAX_ACTOR: usize = 64;
const MAX_ACTION: usize = 48;
const MAX_DETAIL: usize = 512;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Entry {
    pub seq: u64,
    pub ts: i64,
    pub actor: String,
    pub node: String,
    pub action: String,
    pub detail: String,
    pub prev: String,
    pub hash: String,
}

fn limit(value: &str, max: usize) -> String {
    value
        .chars()
        .filter(|c| !c.is_control())
        .take(max)
        .collect()
}

fn feed(hasher: &mut Sha256, part: &[u8]) {
    let length = u32::try_from(part.len()).unwrap_or(u32::MAX);
    hasher.update(length.to_be_bytes());
    hasher.update(part);
}

#[must_use]
pub fn entry_hash(
    prev: &str,
    seq: u64,
    ts: i64,
    actor: &str,
    node: &str,
    action: &str,
    detail: &str,
) -> String {
    let mut hasher = Sha256::new();
    feed(&mut hasher, prev.as_bytes());
    feed(&mut hasher, &seq.to_be_bytes());
    feed(&mut hasher, &ts.to_be_bytes());
    for part in [actor, node, action, detail] {
        feed(&mut hasher, part.as_bytes());
    }
    hexutil::encode(&hasher.finalize())
}

#[must_use]
pub fn seal(
    prev: &str,
    seq: u64,
    ts: i64,
    actor: &str,
    node: &str,
    action: &str,
    detail: &str,
) -> Entry {
    let actor = limit(actor, MAX_ACTOR);
    let node = limit(node, MAX_ACTOR);
    let action = limit(action, MAX_ACTION);
    let detail = limit(detail, MAX_DETAIL);
    let hash = entry_hash(prev, seq, ts, &actor, &node, &action, &detail);
    Entry {
        seq,
        ts,
        actor,
        node,
        action,
        detail,
        prev: prev.to_owned(),
        hash,
    }
}

#[must_use]
pub fn verify_chain(anchor: &str, entries: &[Entry]) -> Option<usize> {
    let mut prev = anchor.to_owned();
    let mut expected = entries.first().map(|e| e.seq);
    for (index, entry) in entries.iter().enumerate() {
        let sound = Some(entry.seq) == expected
            && entry.prev == prev
            && entry.hash
                == entry_hash(
                    &entry.prev,
                    entry.seq,
                    entry.ts,
                    &entry.actor,
                    &entry.node,
                    &entry.action,
                    &entry.detail,
                );
        if !sound {
            return Some(index);
        }
        prev.clone_from(&entry.hash);
        expected = entry.seq.checked_add(1);
    }
    None
}
