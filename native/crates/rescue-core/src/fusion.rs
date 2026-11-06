use std::collections::BTreeMap;

use serde::Serialize;

use crate::policy::Policy;
use crate::signal::{Evidence, Hazard, Kind, Modality};

pub const PRIOR_LOGIT: f64 = -3.0;
pub const GAIN: f64 = 1.6;
pub const SAME_KIND_DISCOUNT: f64 = 0.5;
pub const SAME_MODALITY_DISCOUNT: f64 = 0.85;
pub const P_FLOOR: f64 = 0.001;
pub const MAX_LOGIT: f64 = 9.0;

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Driver {
    pub kind: Kind,
    pub weight: f64,
    pub sources: usize,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct HazardRisk {
    pub hazard: Hazard,
    pub risk: f64,
    pub confidence: f64,
    pub modalities: usize,
    pub drivers: Vec<Driver>,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Assessment {
    pub at: f64,
    pub hazards: Vec<HazardRisk>,
}

impl Assessment {
    #[must_use]
    pub fn of(&self, hazard: Hazard) -> Option<&HazardRisk> {
        self.hazards.iter().find(|h| h.hazard == hazard)
    }

    #[must_use]
    pub fn risk(&self, hazard: Hazard) -> f64 {
        self.of(hazard)
            .map_or_else(|| sigmoid(PRIOR_LOGIT), |h| h.risk)
    }

    #[must_use]
    pub fn top(&self) -> Option<&HazardRisk> {
        self.hazards.iter().max_by(|a, b| a.risk.total_cmp(&b.risk))
    }
}

#[must_use]
pub fn sigmoid(x: f64) -> f64 {
    1.0 / (1.0 + (-x).exp())
}

fn logit(p: f64) -> f64 {
    let p = p.clamp(P_FLOOR, 1.0 - P_FLOOR);
    (p / (1.0 - p)).ln()
}

fn decay(e: &Evidence, now: f64) -> f64 {
    let age = (now - e.at).max(0.0);
    (-age * std::f64::consts::LN_2 / e.kind.half_life()).exp()
}

fn strength(e: &Evidence, policy: &Policy, now: f64) -> f64 {
    let effective = 0.5 + (e.probability - 0.5) * e.confidence;
    let signed = logit(effective) * GAIN * policy.reliability_of(e.kind) * decay(e, now);
    if e.kind.reassuring() { -signed } else { signed }
}

struct Group {
    weights: Vec<f64>,
    certainty: f64,
}

fn collect(evidence: &[Evidence], policy: &Policy, now: f64) -> BTreeMap<Kind, Group> {
    let mut by_source: BTreeMap<(Kind, &str), (f64, f64)> = BTreeMap::new();
    for e in evidence
        .iter()
        .filter(|e| !e.expired(now) && e.at <= now + 5.0)
    {
        let s = strength(e, policy, now);
        let c = e.confidence * policy.reliability_of(e.kind) * decay(e, now);
        let slot = by_source
            .entry((e.kind, e.source.as_str()))
            .or_insert((0.0, 0.0));
        if s.abs() > slot.0.abs() {
            slot.0 = s;
        }
        slot.1 = slot.1.max(c);
    }
    let mut groups: BTreeMap<Kind, Group> = BTreeMap::new();
    for ((kind, _), (s, c)) in by_source {
        let g = groups.entry(kind).or_insert(Group {
            weights: Vec::new(),
            certainty: 1.0,
        });
        g.weights.push(s);
        g.certainty *= 1.0 - c.clamp(0.0, 1.0);
    }
    for g in groups.values_mut() {
        g.weights.sort_by(|a, b| b.abs().total_cmp(&a.abs()));
    }
    groups
}

fn kind_weight(group: &Group) -> f64 {
    let mut factor = 1.0;
    let mut total = 0.0;
    for w in &group.weights {
        total += w * factor;
        factor *= SAME_KIND_DISCOUNT;
    }
    total
}

fn hazard_risk(hazard: Hazard, groups: &BTreeMap<Kind, Group>) -> Option<HazardRisk> {
    let mut drivers: Vec<Driver> = groups
        .iter()
        .filter(|(k, _)| k.hazards().contains(&hazard))
        .map(|(k, g)| Driver {
            kind: *k,
            weight: kind_weight(g),
            sources: g.weights.len(),
        })
        .collect();
    if drivers.is_empty() {
        return None;
    }
    drivers.sort_by(|a, b| {
        b.weight
            .abs()
            .total_cmp(&a.weight.abs())
            .then(a.kind.cmp(&b.kind))
    });
    let mut seen: BTreeMap<Modality, f64> = BTreeMap::new();
    let mut total = PRIOR_LOGIT;
    let mut doubt = 1.0;
    for d in &drivers {
        let factor = seen.entry(d.kind.modality()).or_insert(1.0);
        total += d.weight * *factor;
        *factor *= SAME_MODALITY_DISCOUNT;
        if let Some(g) = groups.get(&d.kind) {
            doubt *= g.certainty;
        }
    }
    let modalities = drivers
        .iter()
        .filter(|d| d.weight > 0.0)
        .map(|d| d.kind.modality())
        .collect::<std::collections::BTreeSet<_>>()
        .len();
    Some(HazardRisk {
        hazard,
        risk: sigmoid(total.clamp(-MAX_LOGIT, MAX_LOGIT)),
        confidence: (1.0 - doubt).clamp(0.0, 1.0),
        modalities,
        drivers,
    })
}

#[must_use]
pub fn assess(evidence: &[Evidence], policy: &Policy, now: f64) -> Assessment {
    let groups = collect(evidence, policy, now);
    let hazards = [
        Hazard::Medical,
        Hazard::Fire,
        Hazard::Intrusion,
        Hazard::Violence,
    ]
    .into_iter()
    .filter_map(|h| hazard_risk(h, &groups))
    .collect();
    Assessment { at: now, hazards }
}
