use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};

use crate::catalog::Catalog;
use crate::segment::{Segment, Tier};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Policy {
    pub continuous_ms: u64,
    pub event_ms: u64,
    pub quota_bytes: u64,
    pub event_pad_ms: u64,
    #[serde(default)]
    pub continuous_overrides: BTreeMap<String, u64>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct RetentionPlan {
    pub promote: Vec<(String, String)>,
    pub expire: Vec<(String, String)>,
    pub evict: Vec<(String, String)>,
    pub kept_bytes: u64,
}

fn near_event(events: &BTreeMap<String, BTreeSet<u64>>, segment: &Segment, pad: u64) -> bool {
    events.get(&segment.camera).is_some_and(|times| {
        let low = segment.start_ms.saturating_sub(pad);
        let high = segment.end_ms().saturating_add(pad);
        times.range(low..=high).next().is_some()
    })
}

fn expired(policy: &Policy, tier: Tier, segment: &Segment, now_ms: u64) -> bool {
    let age = now_ms.saturating_sub(segment.end_ms());
    match tier {
        Tier::Pinned => false,
        Tier::Continuous => {
            age > policy
                .continuous_overrides
                .get(&segment.camera)
                .copied()
                .unwrap_or(policy.continuous_ms)
        }
        Tier::Event => age > policy.event_ms,
    }
}

#[must_use]
pub fn plan(
    catalog: &Catalog,
    policy: &Policy,
    events: &[(String, u64)],
    now_ms: u64,
) -> RetentionPlan {
    let mut grouped: BTreeMap<String, BTreeSet<u64>> = BTreeMap::new();
    for (camera, at) in events {
        grouped.entry(camera.clone()).or_default().insert(*at);
    }
    let mut out = RetentionPlan::default();
    let mut alive: Vec<(Tier, &Segment)> = Vec::new();
    for segment in catalog.iter() {
        let mut tier = segment.tier;
        let promoted =
            tier == Tier::Continuous && near_event(&grouped, segment, policy.event_pad_ms);
        if promoted {
            tier = Tier::Event;
        }
        let key = (segment.camera.clone(), segment.id.clone());
        if expired(policy, tier, segment, now_ms) {
            out.expire.push(key);
            continue;
        }
        if promoted {
            out.promote.push(key);
        }
        alive.push((tier, segment));
    }
    let mut total = alive
        .iter()
        .fold(0u64, |acc, (_, s)| acc.saturating_add(s.bytes));
    if policy.quota_bytes > 0 && total > policy.quota_bytes {
        let mut candidates: Vec<&(Tier, &Segment)> = alive
            .iter()
            .filter(|(tier, _)| *tier != Tier::Pinned)
            .collect();
        candidates.sort_by_key(|(tier, s)| (*tier, s.start_ms, s.camera.clone(), s.id.clone()));
        let mut evicted: BTreeSet<(String, String)> = BTreeSet::new();
        for (_, segment) in candidates {
            if total <= policy.quota_bytes {
                break;
            }
            total = total.saturating_sub(segment.bytes);
            let key = (segment.camera.clone(), segment.id.clone());
            evicted.insert(key.clone());
            out.evict.push(key);
        }
        out.promote.retain(|key| !evicted.contains(key));
    }
    out.kept_bytes = total;
    out
}
