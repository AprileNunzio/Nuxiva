use crate::fusion::{Member, Reading, fuse};
use crate::policy::Policy;
use crate::signal::Signals;
use nuxiva_display_domain::AudienceKind;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Audience {
    pub kind: AudienceKind,
    pub members: Vec<Member>,
    pub guests: u16,
    pub since_ms: u64,
    pub nucleus_only: bool,
}

#[derive(Debug, Clone)]
pub struct Tracker {
    policy: Policy,
    current: AudienceKind,
    since_ms: u64,
    candidate: Option<(AudienceKind, u64)>,
    last_seen_ms: Option<u64>,
    last_voice_ms: Option<u64>,
    members: Vec<Member>,
    guests: u16,
}

const fn rank(kind: AudienceKind) -> u8 {
    match kind {
        AudienceKind::Authorized => 3,
        AudienceKind::Mixed => 2,
        AudienceKind::GuestOnly => 1,
        AudienceKind::Empty | AudienceKind::Uncertain => 0,
    }
}

const fn within(last: Option<u64>, span: u64, now_ms: u64) -> bool {
    match last {
        Some(at) => now_ms.saturating_sub(at) < span,
        None => false,
    }
}

impl Tracker {
    #[must_use]
    pub const fn new(policy: Policy, now_ms: u64) -> Self {
        Self {
            policy,
            current: AudienceKind::Uncertain,
            since_ms: now_ms,
            candidate: None,
            last_seen_ms: None,
            last_voice_ms: None,
            members: Vec::new(),
            guests: 0,
        }
    }

    #[must_use]
    pub const fn policy(&self) -> &Policy {
        &self.policy
    }

    pub fn step(&mut self, signals: &Signals, now_ms: u64) -> Audience {
        let reading = fuse(signals, &self.policy, now_ms);
        self.remember(&reading, now_ms);
        let target = self.target(&reading, now_ms);
        self.advance(target, &reading, now_ms);
        self.audience()
    }

    fn remember(&mut self, reading: &Reading, now_ms: u64) {
        if reading.seen {
            self.last_seen_ms = Some(now_ms);
        }
        if reading.voiced {
            self.last_voice_ms = Some(now_ms);
        }
    }

    fn target(&self, reading: &Reading, now_ms: u64) -> AudienceKind {
        if reading.kind != AudienceKind::Empty || self.current == AudienceKind::Empty {
            return reading.kind;
        }
        let present = within(self.last_seen_ms, self.policy.away_ms, now_ms);
        let speaking = rank(self.current) >= rank(AudienceKind::Mixed)
            && within(self.last_voice_ms, self.policy.voice_hold_ms, now_ms);
        if present || speaking {
            self.current
        } else {
            AudienceKind::Empty
        }
    }

    fn advance(&mut self, target: AudienceKind, reading: &Reading, now_ms: u64) {
        if target == self.current {
            self.candidate = None;
            if reading.kind == target {
                self.adopt(reading);
            }
            return;
        }
        let closing =
            rank(target) < rank(self.current) || rank(target).max(rank(self.current)) <= 1;
        let stable = match self.candidate {
            Some((kind, since)) if kind == target => {
                now_ms.saturating_sub(since) >= self.policy.stable_ms
            }
            _ => {
                self.candidate = Some((target, now_ms));
                false
            }
        };
        if closing || stable {
            self.current = target;
            self.since_ms = now_ms;
            self.candidate = None;
            self.adopt(reading);
        }
    }

    fn adopt(&mut self, reading: &Reading) {
        self.members.clone_from(&reading.members);
        self.guests = reading.guests;
    }

    #[must_use]
    pub fn audience(&self) -> Audience {
        Audience {
            kind: self.current,
            members: self.members.clone(),
            guests: self.guests,
            since_ms: self.since_ms,
            nucleus_only: self.current.nucleus_only(),
        }
    }
}
