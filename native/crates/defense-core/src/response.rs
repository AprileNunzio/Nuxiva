use std::collections::{BTreeMap, BTreeSet};

use crate::incident::clean;
use crate::model::{
    Action, ActionKind, Autonomy, CountryStat, Incident, Input, Mode, Origin, Posture, Severity,
    Stage,
};

pub const MAX_ACTIONS: usize = 200;
pub const RECENT: f64 = 600.0;
pub const ASSIST_MINUTES: u32 = 60;

fn choose(incident: &Incident, input: &Input) -> (ActionKind, &'static str) {
    let policy = &input.policy;
    if incident.protected {
        return (ActionKind::Warn, "protected_source");
    }
    if incident.trusted {
        return (ActionKind::Warn, "trusted_anomaly");
    }
    if incident.origin == Origin::Lan {
        if incident.stage >= Stage::Interception
            && incident.level >= Severity::High
            && policy.quarantine
        {
            return (ActionKind::Quarantine, "lan_compromise");
        }
        return (ActionKind::Warn, "lan_anomaly");
    }
    match incident.stage {
        Stage::Recon if policy.honeypot => (ActionKind::Honeypot, "recon_deception"),
        Stage::Recon if policy.tarpit => (ActionKind::Tarpit, "recon_slowdown"),
        Stage::Recon => (ActionKind::Block, "recon_block"),
        Stage::Disruption if incident.level < Severity::Critical => {
            (ActionKind::RateLimit, "flood_limit")
        }
        Stage::Disruption => (ActionKind::Block, "flood_block"),
        Stage::Exfiltration => (ActionKind::Block, "exfiltration_block"),
        Stage::Intrusion | Stage::Interception => (ActionKind::Block, "intrusion_block"),
    }
}

#[must_use]
pub fn duration(input: &Input, strikes: u32) -> u32 {
    let policy = &input.policy;
    let ceiling = policy.max_minutes.clamp(1, 525_600);
    let base = policy.block_minutes.clamp(1, ceiling);
    let factor = 1_u32.checked_shl(strikes.min(10)).unwrap_or(1024);
    base.saturating_mul(factor).min(ceiling)
}

const fn allowed(autonomy: Autonomy, kind: ActionKind, minutes: u32) -> bool {
    match autonomy {
        Autonomy::Observe => false,
        Autonomy::Assist => {
            minutes <= ASSIST_MINUTES
                && matches!(
                    kind,
                    ActionKind::RateLimit
                        | ActionKind::Tarpit
                        | ActionKind::Honeypot
                        | ActionKind::Block
                )
        }
        Autonomy::Autonomous => true,
    }
}

#[must_use]
pub fn plan(input: &Input, incidents: &[Incident]) -> Vec<Action> {
    let policy = &input.policy;
    let enforcing = matches!(policy.mode, Mode::Protect | Mode::Lockdown);
    let active: BTreeSet<String> = input
        .active
        .iter()
        .take(crate::model::MAX_LIST)
        .filter_map(|a| clean(a))
        .collect();
    let budget = policy
        .max_actions_per_hour
        .saturating_sub(input.recent_actions);
    let mut used = 0_u32;
    let mut actions = Vec::new();
    for incident in incidents {
        if incident.level < policy.min_level {
            continue;
        }
        let (kind, reason) = choose(incident, input);
        if kind != ActionKind::Warn && active.contains(&incident.src) {
            continue;
        }
        let minutes = if kind == ActionKind::Warn {
            0
        } else {
            duration(input, incident.strikes)
        };
        let auto = enforcing
            && kind != ActionKind::Warn
            && allowed(policy.autonomy, kind, minutes)
            && used < budget;
        if auto {
            used = used.saturating_add(1);
        }
        actions.push(Action {
            kind,
            target: incident.src.clone(),
            minutes,
            reason: reason.to_owned(),
            incident: incident.id.clone(),
            auto,
            reversible: true,
        });
    }
    if policy.country_block {
        let home: BTreeSet<String> = policy
            .home_countries
            .iter()
            .map(|c| c.trim().to_ascii_uppercase())
            .collect();
        let threshold = policy.country_threshold.max(2);
        let mut waves: BTreeMap<&str, u32> = BTreeMap::new();
        for incident in incidents {
            if incident.origin == Origin::Internet
                && !incident.country.is_empty()
                && incident.level >= Severity::Medium
                && !incident.trusted
                && !incident.protected
            {
                let slot = waves.entry(incident.country.as_str()).or_insert(0);
                *slot = slot.saturating_add(1);
            }
        }
        for (country, count) in waves {
            let target = format!("country:{country}");
            if count < threshold || home.contains(country) || active.contains(&target) {
                continue;
            }
            let auto = enforcing && policy.autonomy == Autonomy::Autonomous && used < budget;
            if auto {
                used = used.saturating_add(1);
            }
            actions.push(Action {
                kind: ActionKind::CountryBlock,
                target,
                minutes: policy
                    .block_minutes
                    .max(60)
                    .min(policy.max_minutes.clamp(60, 525_600)),
                reason: "country_wave".to_owned(),
                incident: String::new(),
                auto,
                reversible: true,
            });
        }
    }
    actions.truncate(MAX_ACTIONS);
    actions
}

#[must_use]
pub fn countries(incidents: &[Incident]) -> Vec<CountryStat> {
    let mut map: BTreeMap<&str, (u32, Severity)> = BTreeMap::new();
    for incident in incidents {
        if incident.origin != Origin::Internet || incident.country.is_empty() {
            continue;
        }
        let slot = map
            .entry(incident.country.as_str())
            .or_insert((0, Severity::Low));
        slot.0 = slot.0.saturating_add(1);
        slot.1 = slot.1.max(incident.level);
    }
    let mut out: Vec<CountryStat> = map
        .into_iter()
        .map(|(country, (incidents, level))| CountryStat {
            country: country.to_owned(),
            incidents,
            level,
        })
        .collect();
    out.sort_by(|a, b| {
        b.incidents
            .cmp(&a.incidents)
            .then(a.country.cmp(&b.country))
    });
    out
}

#[must_use]
pub fn posture(now: f64, incidents: &[Incident]) -> Posture {
    match incidents
        .iter()
        .filter(|i| now - i.last_at <= RECENT)
        .map(|i| i.level)
        .max()
    {
        None => Posture::Calm,
        Some(Severity::Low | Severity::Medium) => Posture::Watch,
        Some(Severity::High) => Posture::Alert,
        Some(Severity::Critical) => Posture::Attack,
    }
}
