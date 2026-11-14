use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::envelope::{Envelope, Level, Scalar};
use crate::smoke::{Check, CheckResult, Severity, Status, evaluate};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Verdict {
    Pass,
    Warn,
    Fail,
    Insufficient,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct DomainStat {
    pub total: u64,
    pub warn: u64,
    pub error: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ErrorStat {
    pub domain: String,
    pub kind: String,
    pub count: u64,
    pub first_ms: u64,
    pub last_ms: u64,
    pub sample_seq: u64,
    pub sample_corr: Option<String>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct Latency {
    pub n: u64,
    pub p50: f64,
    pub p95: f64,
    pub max: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Report {
    pub from_ms: u64,
    pub to_ms: u64,
    pub events: u64,
    pub domains: BTreeMap<String, DomainStat>,
    pub errors: Vec<ErrorStat>,
    pub latency: BTreeMap<String, Latency>,
    pub checks: Vec<CheckResult>,
    pub verdict: Verdict,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Regression {
    pub subject: String,
    pub kind: String,
    pub before: Option<f64>,
    pub after: Option<f64>,
}

fn percentile(sorted: &[f64], q: f64) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    #[allow(
        clippy::cast_precision_loss,
        clippy::cast_possible_truncation,
        clippy::cast_sign_loss
    )]
    let rank = (q * sorted.len() as f64).ceil() as usize;
    sorted
        .get(rank.saturating_sub(1).min(sorted.len().saturating_sub(1)))
        .copied()
        .unwrap_or(0.0)
}

fn verdict_for(events: u64, checks: &[CheckResult]) -> Verdict {
    if events == 0 {
        return Verdict::Insufficient;
    }
    let failed = |sev: fn(Severity) -> bool| {
        checks
            .iter()
            .any(|c| c.status == Status::Fail && sev(c.severity))
    };
    if failed(|s| s >= Severity::Major) {
        Verdict::Fail
    } else if failed(|_| true) || checks.iter().any(|c| c.status == Status::Missing) {
        Verdict::Warn
    } else {
        Verdict::Pass
    }
}

#[must_use]
pub fn analyze(events: &[Envelope], spec: &[Check]) -> Report {
    let mut domains: BTreeMap<String, DomainStat> = BTreeMap::new();
    let mut errors: BTreeMap<(String, String), ErrorStat> = BTreeMap::new();
    let mut latencies: BTreeMap<String, Vec<f64>> = BTreeMap::new();
    let from_ms = events.iter().map(|e| e.at_ms).min().unwrap_or(0);
    let to_ms = events.iter().map(|e| e.at_ms).max().unwrap_or(0);
    for e in events {
        let stat = domains.entry(e.domain.as_str().to_owned()).or_default();
        stat.total = stat.total.saturating_add(1);
        if e.level == Level::Warn {
            stat.warn = stat.warn.saturating_add(1);
        }
        if e.level >= Level::Error {
            stat.error = stat.error.saturating_add(1);
            let entry = errors
                .entry((e.domain.as_str().to_owned(), e.kind.clone()))
                .or_insert_with(|| ErrorStat {
                    domain: e.domain.as_str().to_owned(),
                    kind: e.kind.clone(),
                    count: 0,
                    first_ms: e.at_ms,
                    last_ms: e.at_ms,
                    sample_seq: e.seq,
                    sample_corr: e.corr.clone(),
                });
            entry.count = entry.count.saturating_add(1);
            entry.last_ms = entry.last_ms.max(e.at_ms);
        }
        if let Some(ms) = e
            .fields
            .get("latency_ms")
            .and_then(Scalar::as_f64)
            .filter(|v| v.is_finite())
        {
            latencies
                .entry(format!("{}.{}", e.domain.as_str(), e.kind))
                .or_default()
                .push(ms);
        }
    }
    let mut errors: Vec<ErrorStat> = errors.into_values().collect();
    errors.sort_by(|a, b| b.count.cmp(&a.count).then(a.kind.cmp(&b.kind)));
    errors.truncate(25);
    let latency = latencies
        .into_iter()
        .map(|(k, mut v)| {
            v.sort_by(f64::total_cmp);
            let n = u64::try_from(v.len()).unwrap_or(u64::MAX);
            let stat = Latency {
                n,
                p50: percentile(&v, 0.5),
                p95: percentile(&v, 0.95),
                max: v.last().copied().unwrap_or(0.0),
            };
            (k, stat)
        })
        .collect();
    let checks = evaluate(spec, events);
    let total = u64::try_from(events.len()).unwrap_or(u64::MAX);
    let verdict = verdict_for(total, &checks);
    Report {
        from_ms,
        to_ms,
        events: total,
        domains,
        errors,
        latency,
        checks,
        verdict,
    }
}

#[must_use]
pub fn compare(before: &Report, after: &Report) -> Vec<Regression> {
    let mut out = Vec::new();
    for now in &after.checks {
        let was = before.checks.iter().find(|c| c.id == now.id);
        if now.status == Status::Fail && was.is_some_and(|w| w.status == Status::Pass) {
            out.push(Regression {
                subject: now.id.clone(),
                kind: "check".to_owned(),
                before: None,
                after: now.worst,
            });
        }
    }
    for (key, now) in &after.latency {
        if let Some(was) = before.latency.get(key) {
            if was.n >= 3 && now.n >= 3 && now.p95 > was.p95 * 1.25 && now.p95 - was.p95 > 5.0 {
                out.push(Regression {
                    subject: key.clone(),
                    kind: "latency_p95".to_owned(),
                    before: Some(was.p95),
                    after: Some(now.p95),
                });
            }
        }
    }
    for now in &after.errors {
        let prev = before
            .errors
            .iter()
            .find(|e| e.domain == now.domain && e.kind == now.kind)
            .map_or(0, |e| e.count);
        if now.count > prev {
            #[allow(clippy::cast_precision_loss)]
            out.push(Regression {
                subject: format!("{}.{}", now.domain, now.kind),
                kind: "errors".to_owned(),
                before: Some(prev as f64),
                after: Some(now.count as f64),
            });
        }
    }
    out
}
