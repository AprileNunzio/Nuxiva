use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::envelope::{Domain, Envelope, Level, Scalar};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Severity {
    Minor,
    Major,
    Critical,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Bound {
    pub field: String,
    #[serde(default)]
    pub min: Option<f64>,
    #[serde(default)]
    pub max: Option<f64>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Rule {
    Expect {
        min_count: u32,
        #[serde(default)]
        equals: BTreeMap<String, Scalar>,
        #[serde(default)]
        bounds: Vec<Bound>,
    },
    Absent {
        min_level: Level,
    },
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Check {
    pub id: String,
    pub hint: String,
    pub domain: Domain,
    pub kind: String,
    pub severity: Severity,
    pub rule: Rule,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Status {
    Pass,
    Fail,
    Missing,
    Skip,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CheckResult {
    pub id: String,
    pub hint: String,
    pub status: Status,
    pub severity: Severity,
    pub count: u32,
    pub evidence: Vec<u64>,
    pub worst: Option<f64>,
}

fn bound(field: &str, min: Option<f64>, max: Option<f64>) -> Bound {
    Bound {
        field: field.to_owned(),
        min,
        max,
    }
}

fn probe(id: &str, kind: &str, severity: Severity, bounds: Vec<Bound>) -> Check {
    let equals = BTreeMap::from([("outcome".to_owned(), Scalar::Text("ok".to_owned()))]);
    Check {
        id: id.to_owned(),
        hint: format!("collaudo.hint.{id}"),
        domain: Domain::Probe,
        kind: kind.to_owned(),
        severity,
        rule: Rule::Expect {
            min_count: 1,
            equals,
            bounds,
        },
    }
}

#[must_use]
#[allow(clippy::too_many_lines)]
pub fn default_spec() -> Vec<Check> {
    vec![
        probe(
            "services",
            "services",
            Severity::Critical,
            vec![bound("inactive", None, Some(0.0))],
        ),
        probe(
            "bus_roundtrip",
            "bus_roundtrip",
            Severity::Major,
            vec![bound("latency_ms", None, Some(100.0))],
        ),
        probe(
            "camera_frame",
            "camera_frame",
            Severity::Critical,
            vec![
                bound("frames", Some(1.0), None),
                bound("latency_ms", None, Some(2500.0)),
            ],
        ),
        probe(
            "microphone_level",
            "microphone_level",
            Severity::Critical,
            vec![bound("level_db", Some(-80.0), Some(-3.0))],
        ),
        probe(
            "ear_roundtrip",
            "ear_roundtrip",
            Severity::Major,
            vec![bound("latency_ms", None, Some(1500.0))],
        ),
        probe(
            "voice_first_audio",
            "voice_first_audio",
            Severity::Major,
            vec![bound("latency_ms", None, Some(800.0))],
        ),
        probe(
            "barge_in",
            "barge_in",
            Severity::Major,
            vec![bound("stop_ms", None, Some(300.0))],
        ),
        probe(
            "aec_erle",
            "aec_erle",
            Severity::Minor,
            vec![bound("erle_db", Some(10.0), None)],
        ),
        probe(
            "sentinel_chain",
            "sentinel_chain",
            Severity::Critical,
            Vec::new(),
        ),
        probe(
            "collaudo_chain",
            "collaudo_chain",
            Severity::Major,
            Vec::new(),
        ),
        probe(
            "mcp_discovery",
            "mcp_discovery",
            Severity::Major,
            vec![bound("tools", Some(1.0), None)],
        ),
        probe("sandbox_exec", "sandbox_exec", Severity::Major, Vec::new()),
        probe(
            "parity",
            "parity",
            Severity::Major,
            vec![bound("failed", None, Some(0.0))],
        ),
        probe(
            "radio_rejected",
            "radio_rejected",
            Severity::Major,
            vec![
                bound("programme_s", Some(1.0), None),
                bound("accepted_n", None, Some(0.0)),
            ],
        ),
        probe(
            "music_rejected",
            "music_rejected",
            Severity::Major,
            vec![
                bound("programme_s", Some(1.0), None),
                bound("accepted_n", None, Some(0.0)),
            ],
        ),
        probe(
            "owner_voice_accepted",
            "owner_voice_accepted",
            Severity::Critical,
            vec![bound("accepted_n", Some(1.0), None)],
        ),
        Check {
            id: "no_runtime_errors".to_owned(),
            hint: "collaudo.hint.no_runtime_errors".to_owned(),
            domain: Domain::Error,
            kind: String::new(),
            severity: Severity::Critical,
            rule: Rule::Absent {
                min_level: Level::Error,
            },
        },
    ]
}

fn within(env: &Envelope, bounds: &[Bound]) -> Option<f64> {
    let mut worst: Option<f64> = None;
    for b in bounds {
        let Some(value) = env.fields.get(&b.field).and_then(Scalar::as_f64) else {
            return Some(f64::NAN);
        };
        if b.min.is_some_and(|m| value < m) || b.max.is_some_and(|m| value > m) {
            return Some(value);
        }
        worst = Some(worst.map_or(value, |w| w.max(value)));
    }
    None
}

fn satisfies(
    env: &Envelope,
    equals: &BTreeMap<String, Scalar>,
    bounds: &[Bound],
) -> (bool, Option<f64>) {
    let eq = equals
        .iter()
        .all(|(k, v)| env.fields.get(k).is_some_and(|f| f.matches(v)));
    let bad = within(env, bounds);
    let value = bounds
        .first()
        .and_then(|b| env.fields.get(&b.field))
        .and_then(Scalar::as_f64);
    (eq && bad.is_none(), bad.or(value))
}

fn skipped(env: &Envelope) -> bool {
    matches!(env.fields.get("outcome"), Some(Scalar::Text(t)) if t == "skip")
}

fn trimmed(mut seqs: Vec<u64>) -> Vec<u64> {
    let keep = seqs.len().saturating_sub(3);
    seqs.drain(..keep);
    seqs
}

#[must_use]
pub fn evaluate(spec: &[Check], events: &[Envelope]) -> Vec<CheckResult> {
    spec.iter()
        .map(|check| evaluate_one(check, events))
        .collect()
}

fn evaluate_one(check: &Check, events: &[Envelope]) -> CheckResult {
    let mut result = CheckResult {
        id: check.id.clone(),
        hint: check.hint.clone(),
        status: Status::Missing,
        severity: check.severity,
        count: 0,
        evidence: Vec::new(),
        worst: None,
    };
    match &check.rule {
        Rule::Absent { min_level } => {
            let offending: Vec<&Envelope> = events
                .iter()
                .filter(|e| {
                    e.domain == check.domain
                        && e.level >= *min_level
                        && e.kind.starts_with(&check.kind)
                })
                .collect();
            result.count = u32::try_from(offending.len()).unwrap_or(u32::MAX);
            result.evidence = trimmed(offending.iter().map(|e| e.seq).collect());
            result.status = if !offending.is_empty() {
                Status::Fail
            } else if events.is_empty() {
                Status::Missing
            } else {
                Status::Pass
            };
        }
        Rule::Expect {
            min_count,
            equals,
            bounds,
        } => {
            let candidates: Vec<&Envelope> = events
                .iter()
                .filter(|e| e.domain == check.domain && e.kind == check.kind)
                .collect();
            let live: Vec<&&Envelope> = candidates.iter().filter(|e| !skipped(e)).collect();
            if candidates.is_empty() {
                return result;
            }
            if live.is_empty() {
                result.status = Status::Skip;
                return result;
            }
            let judged: Vec<(bool, Option<f64>, u64)> = live
                .iter()
                .map(|e| {
                    let (ok, worst) = satisfies(e, equals, bounds);
                    (ok, worst, e.seq)
                })
                .collect();
            let good = judged.iter().filter(|(ok, _, _)| *ok).count();
            result.count = u32::try_from(good).unwrap_or(u32::MAX);
            result.evidence = trimmed(judged.iter().map(|(_, _, s)| *s).collect());
            let last = judged.last();
            result.worst = last.and_then(|(_, w, _)| *w).filter(|w| w.is_finite());
            let latest_ok = last.is_some_and(|(ok, _, _)| *ok);
            result.status = if latest_ok && result.count >= *min_count {
                Status::Pass
            } else {
                Status::Fail
            };
        }
    }
    result
}
