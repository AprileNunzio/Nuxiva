use crate::ledger::Ledger;
use crate::wire::Wire;
use std::collections::BTreeSet;

pub const BROADCAST_WAIT_MS: i64 = 800;
pub const PEER_WAIT_MS: i64 = 1_500;
pub const TOTAL_MS: i64 = 12_000;
pub const MAX_PEERS_ASKED: usize = 8;
pub const BACKOFF_BASE_MS: u64 = 1_000;
pub const BACKOFF_CAP_MS: u64 = 60_000;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Action {
    Dial(String),
    Broadcast(Wire),
    Query { peer: String, wire: Wire },
    Wait { until: i64 },
    GiveUp,
    Connected,
}

#[derive(Debug, Clone)]
pub struct Lookup {
    id: String,
    started: i64,
    tried: BTreeSet<String>,
    asked: BTreeSet<String>,
    broadcast_at: Option<i64>,
    last_query: Option<i64>,
    connected: bool,
}

impl Lookup {
    #[must_use]
    pub fn new(id: &str, now: i64) -> Self {
        Self {
            id: id.to_owned(),
            started: now,
            tried: BTreeSet::new(),
            asked: BTreeSet::new(),
            broadcast_at: None,
            last_query: None,
            connected: false,
        }
    }

    #[must_use]
    pub fn id(&self) -> &str {
        &self.id
    }

    pub fn next(&mut self, ledger: &Ledger, peers: &[String], now: i64) -> Action {
        if self.connected {
            return Action::Connected;
        }
        if let Some(addr) = ledger
            .candidates(&self.id)
            .into_iter()
            .find(|addr| !self.tried.contains(addr))
        {
            self.tried.insert(addr.clone());
            return Action::Dial(addr);
        }
        if now.saturating_sub(self.started) > TOTAL_MS {
            return Action::GiveUp;
        }
        let Some(sent) = self.broadcast_at else {
            self.broadcast_at = Some(now);
            return Action::Broadcast(Wire::Want {
                id: self.id.clone(),
            });
        };
        let broadcast_until = sent.saturating_add(BROADCAST_WAIT_MS);
        if now < broadcast_until {
            return Action::Wait {
                until: broadcast_until,
            };
        }
        if self.asked.len() < MAX_PEERS_ASKED {
            if let Some(peer) = peers.iter().find(|peer| !self.asked.contains(*peer)) {
                self.asked.insert(peer.clone());
                self.last_query = Some(now);
                return Action::Query {
                    peer: peer.clone(),
                    wire: Wire::Want {
                        id: self.id.clone(),
                    },
                };
            }
        }
        let peer_until = self
            .last_query
            .map_or(now, |at| at.saturating_add(PEER_WAIT_MS));
        if now < peer_until {
            return Action::Wait { until: peer_until };
        }
        Action::GiveUp
    }

    pub fn dialed(&mut self, ledger: &mut Ledger, addr: &str, reached: bool) {
        if reached {
            ledger.report_success(&self.id, addr);
            self.connected = true;
        } else {
            ledger.report_failure(&self.id, addr);
        }
    }
}

#[must_use]
pub fn reconnect_delay_ms(attempt: u32, jitter: u64) -> u64 {
    let exponent = attempt.min(16);
    let base = BACKOFF_BASE_MS
        .saturating_mul(1u64 << exponent)
        .min(BACKOFF_CAP_MS);
    let spread = (base / 4).max(1);
    base.saturating_add(jitter.checked_rem(spread).unwrap_or(0))
}
