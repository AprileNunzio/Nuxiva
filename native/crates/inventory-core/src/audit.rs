use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Entry {
    pub seq: u64,
    pub at_ms: u64,
    pub event: String,
    pub prev: [u8; 32],
    pub hash: [u8; 32],
}

fn seal(seq: u64, at_ms: u64, event: &str, prev: &[u8; 32]) -> [u8; 32] {
    let mut hasher = blake3::Hasher::new();
    hasher.update(&seq.to_le_bytes());
    hasher.update(&at_ms.to_le_bytes());
    hasher.update(prev);
    hasher.update(event.as_bytes());
    *hasher.finalize().as_bytes()
}

#[derive(Debug, Clone, Default)]
pub struct Chain {
    entries: Vec<Entry>,
}

impl Chain {
    pub fn append(&mut self, at_ms: u64, event: String) {
        let prev = self.entries.last().map_or([0; 32], |e| e.hash);
        let seq = u64::try_from(self.entries.len()).unwrap_or(u64::MAX);
        let hash = seal(seq, at_ms, &event, &prev);
        self.entries.push(Entry {
            seq,
            at_ms,
            event,
            prev,
            hash,
        });
    }

    #[must_use]
    pub fn entries(&self) -> &[Entry] {
        &self.entries
    }

    #[must_use]
    pub fn verify(entries: &[Entry]) -> bool {
        let mut prev = [0u8; 32];
        for (index, entry) in entries.iter().enumerate() {
            let seq = u64::try_from(index).unwrap_or(u64::MAX);
            if entry.seq != seq
                || entry.prev != prev
                || entry.hash != seal(entry.seq, entry.at_ms, &entry.event, &entry.prev)
            {
                return false;
            }
            prev = entry.hash;
        }
        true
    }
}
