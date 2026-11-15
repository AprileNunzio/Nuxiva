use crate::envelope::Envelope;
use sha2::{Digest, Sha256};
use std::collections::{BTreeSet, VecDeque};

pub const SEEN_CAPACITY: usize = 8192;

#[derive(Debug, Clone)]
pub struct Gossip {
    seen: BTreeSet<String>,
    order: VecDeque<String>,
    capacity: usize,
    fanout: usize,
}

impl Gossip {
    #[must_use]
    pub fn new(fanout: usize) -> Self {
        Self {
            seen: BTreeSet::new(),
            order: VecDeque::new(),
            capacity: SEEN_CAPACITY,
            fanout: fanout.max(1),
        }
    }

    pub fn first_seen(&mut self, envelope: &Envelope) -> bool {
        let id = envelope.message_id();
        if self.seen.contains(&id) {
            return false;
        }
        if self.order.len() >= self.capacity {
            if let Some(old) = self.order.pop_front() {
                self.seen.remove(&old);
            }
        }
        self.seen.insert(id.clone());
        self.order.push_back(id);
        true
    }

    #[must_use]
    pub fn targets(
        &self,
        me: &str,
        envelope: &Envelope,
        came_from: Option<&str>,
        peers: &[String],
    ) -> Vec<String> {
        if envelope.ttl == 0 {
            return Vec::new();
        }
        let message = envelope.message_id();
        let mut hasher = Sha256::new();
        hasher.update(me.as_bytes());
        hasher.update(message.as_bytes());
        let digest: [u8; 32] = hasher.finalize().into();
        let mut state = digest
            .get(..8)
            .and_then(|s| <[u8; 8]>::try_from(s).ok())
            .map_or(1, u64::from_be_bytes)
            | 1;
        let mut pool: Vec<&String> = peers
            .iter()
            .filter(|p| p.as_str() != me && Some(p.as_str()) != came_from && **p != envelope.from)
            .collect();
        let mut chosen = Vec::new();
        while chosen.len() < self.fanout && !pool.is_empty() {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            let len = u64::try_from(pool.len()).unwrap_or(1);
            let pick = usize::try_from(state.checked_rem(len).unwrap_or(0)).unwrap_or(0);
            chosen.push(pool.swap_remove(pick).clone());
        }
        chosen
    }
}
