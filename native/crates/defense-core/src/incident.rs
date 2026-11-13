use std::collections::{BTreeMap, BTreeSet};

use crate::model::{Incident, Input, Kind, MAX_ALERTS, MAX_TEXT, Origin, Severity, Stage};
use crate::net::{self, Net};

pub const MAX_INCIDENTS: usize = 200;
pub const MAX_TARGETS: usize = 16;

#[must_use]
pub const fn stage_of(kind: Kind) -> Stage {
    match kind {
        Kind::PortScan | Kind::HostSweep => Stage::Recon,
        Kind::SynFlood | Kind::IcmpFlood => Stage::Disruption,
        Kind::BruteForce => Stage::Intrusion,
        Kind::ArpSpoof => Stage::Interception,
        Kind::DnsTunnel | Kind::Exfiltration => Stage::Exfiltration,
    }
}

const fn severity_points(severity: Severity) -> u32 {
    match severity {
        Severity::Low => 10,
        Severity::Medium => 30,
        Severity::High => 55,
        Severity::Critical => 80,
    }
}

const fn stage_points(stage: Stage) -> u32 {
    match stage {
        Stage::Recon => 0,
        Stage::Disruption => 5,
        Stage::Intrusion => 10,
        Stage::Interception | Stage::Exfiltration => 15,
    }
}

#[must_use]
pub const fn level_of(score: u32) -> Severity {
    if score < 25 {
        Severity::Low
    } else if score < 50 {
        Severity::Medium
    } else if score < 75 {
        Severity::High
    } else {
        Severity::Critical
    }
}

#[must_use]
pub fn fingerprint(text: &str) -> String {
    let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
    for byte in text.bytes() {
        hash ^= u64::from(byte);
        hash = hash.wrapping_mul(0x0100_0000_01b3);
    }
    format!("{hash:016x}")
}

#[must_use]
pub fn window(raw: f64) -> f64 {
    if raw.is_finite() && raw > 0.0 {
        raw.clamp(60.0, 86_400.0)
    } else {
        1800.0
    }
}

#[must_use]
pub fn clean(raw: &str) -> Option<String> {
    let text = raw.trim();
    if text.is_empty() || !text.bytes().all(|b| b.is_ascii_graphic()) {
        return None;
    }
    let canonical = net::canonical(text);
    Some(canonical.chars().take(MAX_TEXT).collect())
}

#[must_use]
pub fn valid_country(raw: &str) -> Option<String> {
    let bytes = raw.as_bytes();
    match bytes {
        [a, b] if a.is_ascii_uppercase() && b.is_ascii_uppercase() && bytes != b"ZZ" => {
            Some(raw.to_owned())
        }
        _ => None,
    }
}

#[derive(Default)]
struct Acc {
    kinds: BTreeSet<Kind>,
    severity: Option<Severity>,
    alerts: u32,
    events: u64,
    targets: BTreeSet<String>,
    first_at: f64,
    last_at: f64,
}

#[must_use]
pub fn trusted_nets(raw: &[String]) -> Vec<Net> {
    raw.iter()
        .take(crate::model::MAX_LIST)
        .filter_map(|t| net::net(t))
        .collect()
}

#[must_use]
pub fn correlate(input: &Input) -> Vec<Incident> {
    let span = window(input.policy.window_s);
    let trusted = trusted_nets(&input.trusted);
    let protected: BTreeSet<String> = input
        .protected
        .iter()
        .take(crate::model::MAX_LIST)
        .filter_map(|p| clean(p))
        .collect();
    let mut groups: BTreeMap<String, Acc> = BTreeMap::new();
    for alert in input.alerts.iter().take(MAX_ALERTS) {
        if !alert.at.is_finite() || input.now - alert.at > span || alert.at > input.now + 60.0 {
            continue;
        }
        let Some(src) = clean(&alert.src) else {
            continue;
        };
        let acc = groups.entry(src).or_insert_with(|| Acc {
            first_at: alert.at,
            last_at: alert.at,
            ..Acc::default()
        });
        acc.kinds.insert(alert.kind);
        acc.severity = Some(
            acc.severity
                .map_or(alert.severity, |s| s.max(alert.severity)),
        );
        acc.alerts = acc.alerts.saturating_add(1);
        acc.events = acc.events.saturating_add(alert.count.max(1));
        acc.first_at = acc.first_at.min(alert.at);
        acc.last_at = acc.last_at.max(alert.at);
        if acc.targets.len() < MAX_TARGETS {
            if let Some(dst) = clean(&alert.dst) {
                acc.targets.insert(dst);
            }
        }
    }
    let mut out: Vec<Incident> = groups
        .into_iter()
        .map(|(src, acc)| build(input, &trusted, &protected, src, acc))
        .collect();
    out.sort_by(|a, b| {
        b.score
            .cmp(&a.score)
            .then(b.last_at.total_cmp(&a.last_at))
            .then(a.src.cmp(&b.src))
    });
    out.truncate(MAX_INCIDENTS);
    out
}

fn build(
    input: &Input,
    trusted: &[Net],
    protected: &BTreeSet<String>,
    src: String,
    acc: Acc,
) -> Incident {
    let addr = net::address(&src);
    let origin = match addr {
        Some(a) if !net::is_lan(&a) => Origin::Internet,
        _ => Origin::Lan,
    };
    let country = if origin == Origin::Internet {
        input
            .countries
            .get(&src)
            .and_then(|c| valid_country(c))
            .unwrap_or_default()
    } else {
        String::new()
    };
    let stages: Vec<Stage> = acc
        .kinds
        .iter()
        .map(|k| stage_of(*k))
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    let stage = stages.last().copied().unwrap_or(Stage::Recon);
    let severity = acc.severity.unwrap_or(Severity::Low);
    let strikes = input.strikes.get(&src).copied().unwrap_or(0).min(1000);
    let diversity = u32::try_from(acc.kinds.len())
        .unwrap_or(u32::MAX)
        .saturating_sub(1)
        .saturating_mul(6);
    let score = severity_points(severity)
        .saturating_add(diversity)
        .saturating_add(acc.alerts.min(15))
        .saturating_add(stage_points(stage))
        .saturating_add(strikes.saturating_mul(5).min(20))
        .min(100);
    Incident {
        id: fingerprint(&src),
        trusted: addr.is_some_and(|a| trusted.iter().any(|t| net::contains(t, &a))),
        protected: protected.contains(&src),
        origin,
        country,
        kinds: acc.kinds.into_iter().collect(),
        stage,
        stages,
        severity,
        level: level_of(score),
        score,
        alerts: acc.alerts,
        events: acc.events,
        targets: acc.targets.into_iter().collect(),
        first_at: acc.first_at,
        last_at: acc.last_at,
        strikes,
        src,
    }
}
