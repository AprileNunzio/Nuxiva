use std::collections::BTreeMap;

use nuxiva_collaudo_core::Verdict;
use serde::{Deserialize, Serialize};

use crate::barge::{self, BargeReport};
use crate::error::BenchResult;
use crate::latency::{self, LatencyReport};
use crate::observations::{Observations, SCHEMA, Source};
use crate::speaker::{self, SpeakerReport};
use crate::stats::{round3, round6};
use crate::thresholds::Thresholds;
use crate::wake::{self, WakeReport};
use crate::wer::{self, WerReport};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Severity {
    Warn,
    Fail,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Violation {
    pub metric: String,
    pub observed: f64,
    pub limit: f64,
    pub severity: Severity,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Regression {
    pub metric: String,
    pub before: f64,
    pub after: f64,
    pub allowed: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BenchReport {
    pub schema: u32,
    pub source: Source,
    pub corpus: String,
    pub fingerprint: String,
    pub latency: Option<LatencyReport>,
    pub wer: Option<WerReport>,
    pub wake: Option<WakeReport>,
    pub speaker: Option<SpeakerReport>,
    pub barge: Option<BargeReport>,
    pub violations: Vec<Violation>,
    pub insufficient: Vec<String>,
    pub regressions: Vec<Regression>,
    pub verdict: Verdict,
}

impl BenchReport {
    #[must_use]
    pub fn metrics(&self) -> BTreeMap<&'static str, f64> {
        let mut m = BTreeMap::new();
        if let Some(l) = &self.latency {
            m.insert("e2e_p50_ms", l.end_to_end.p50);
            m.insert("e2e_p95_ms", l.end_to_end.p95);
            m.insert("e2e_p99_ms", l.end_to_end.p99);
        }
        if let Some(w) = &self.wer {
            m.insert("wer", w.wer);
        }
        if let Some(w) = &self.wake {
            m.insert("wake_miss_rate", w.miss_rate);
            m.insert("wake_false_accepts_per_hour", w.false_accepts_per_hour);
            m.insert(
                "wake_background_false_accepts_per_hour",
                w.background_false_accepts_per_hour,
            );
        }
        if let Some(s) = &self.speaker {
            m.insert("known_miss_rate", s.known_miss_rate);
            m.insert("false_known_rate", s.false_known_rate);
            m.insert("guest_as_known_rate", s.guest_as_known_rate);
            m.insert("broadcast_as_known_rate", s.broadcast_as_known_rate);
            m.insert("background_false_known_rate", s.background_false_known_rate);
        }
        if let Some(b) = &self.barge {
            m.insert("barge_miss_rate", b.miss_rate);
            m.insert("barge_false_rate", b.false_rate);
            m.insert("barge_background_false_rate", b.background_false_rate);
            m.insert("barge_reaction_p95_ms", b.reaction.p95);
        }
        m
    }
}

fn gate(
    section: &str,
    present: bool,
    enough: bool,
    th: &Thresholds,
    insufficient: &mut Vec<String>,
) {
    let required = th.required.iter().any(|s| s == section);
    if (!present && required) || (present && !enough) {
        insufficient.push(section.to_owned());
    }
}

fn verdict_of(
    violations: &[Violation],
    insufficient: &[String],
    regressions: &[Regression],
) -> Verdict {
    if !regressions.is_empty() || violations.iter().any(|v| v.severity == Severity::Fail) {
        Verdict::Fail
    } else if !insufficient.is_empty() {
        Verdict::Insufficient
    } else if violations.is_empty() {
        Verdict::Pass
    } else {
        Verdict::Warn
    }
}

struct Sections {
    latency: Option<LatencyReport>,
    wer: Option<WerReport>,
    wake: Option<WakeReport>,
    speaker: Option<SpeakerReport>,
    barge: Option<BargeReport>,
}

fn measure(obs: &Observations) -> BenchResult<Sections> {
    let (latency, wer) = if obs.utterances.is_empty() {
        (None, None)
    } else {
        let times: Vec<_> = obs.utterances.iter().map(|u| u.stages).collect();
        let pairs = obs
            .utterances
            .iter()
            .map(|u| (u.reference.as_str(), u.hypothesis.as_str()));
        (Some(latency::analyze(&times)?), Some(wer::analyze(pairs)?))
    };
    Ok(Sections {
        latency,
        wer,
        wake: if obs.wake.is_empty() {
            None
        } else {
            Some(wake::analyze(&obs.wake)?)
        },
        speaker: if obs.speaker.is_empty() {
            None
        } else {
            Some(speaker::analyze(&obs.speaker))
        },
        barge: if obs.barge.is_empty() {
            None
        } else {
            Some(barge::analyze(&obs.barge)?)
        },
    })
}

fn sufficiency(obs: &Observations, s: &Sections, th: &Thresholds) -> Vec<String> {
    let mut insufficient = Vec::new();
    let utterances = u64::try_from(obs.utterances.len()).unwrap_or(u64::MAX);
    let enough = utterances >= th.min_utterances;
    gate(
        "latency",
        s.latency.is_some(),
        enough,
        th,
        &mut insufficient,
    );
    gate("wer", s.wer.is_some(), enough, th, &mut insufficient);
    let wake_ok = s.wake.as_ref().is_some_and(|w| {
        w.positives >= th.min_wake_positives && w.negative_hours >= th.min_wake_negative_hours
    });
    gate("wake", s.wake.is_some(), wake_ok, th, &mut insufficient);
    let speaker_ok = s
        .speaker
        .as_ref()
        .is_some_and(|x| x.trials >= th.min_speaker_trials);
    gate(
        "speaker",
        s.speaker.is_some(),
        speaker_ok,
        th,
        &mut insufficient,
    );
    let barge_ok = s
        .barge
        .as_ref()
        .is_some_and(|b| b.trials >= th.min_barge_trials);
    gate("barge", s.barge.is_some(), barge_ok, th, &mut insufficient);
    insufficient
}

fn violations(report: &BenchReport, th: &Thresholds) -> Vec<Violation> {
    let metrics = report.metrics();
    let mut found = Vec::new();
    for (name, limit) in th.rules() {
        let Some(value) = metrics.get(name).copied() else {
            continue;
        };
        let (severity, bound) = if value > limit.fail {
            (Severity::Fail, limit.fail)
        } else if value > limit.warn {
            (Severity::Warn, limit.warn)
        } else {
            continue;
        };
        found.push(Violation {
            metric: name.to_owned(),
            observed: value,
            limit: bound,
            severity,
        });
    }
    found
}

pub fn run(obs: &Observations, th: &Thresholds) -> BenchResult<BenchReport> {
    obs.validate()?;
    th.validate()?;
    let sections = measure(obs)?;
    let insufficient = sufficiency(obs, &sections, th);
    let mut report = BenchReport {
        schema: SCHEMA,
        source: obs.source,
        corpus: obs.corpus.clone(),
        fingerprint: obs.fingerprint()?,
        latency: sections.latency,
        wer: sections.wer,
        wake: sections.wake,
        speaker: sections.speaker,
        barge: sections.barge,
        violations: Vec::new(),
        insufficient,
        regressions: Vec::new(),
        verdict: Verdict::Pass,
    };
    report.violations = violations(&report, th);
    report.verdict = verdict_of(
        &report.violations,
        &report.insufficient,
        &report.regressions,
    );
    Ok(report)
}

pub fn compare(baseline: &BenchReport, current: &mut BenchReport, th: &Thresholds) {
    let before = baseline.metrics();
    let after = current.metrics();
    let mut found = Vec::new();
    for (name, now) in &after {
        let Some(was) = before.get(name).copied() else {
            continue;
        };
        let allowed = if name.ends_with("_ms") {
            round3(was * (1.0 + th.tolerance.latency_ratio))
        } else {
            round6(was + th.tolerance.rate_abs)
        };
        if *now > allowed {
            found.push(Regression {
                metric: (*name).to_owned(),
                before: was,
                after: *now,
                allowed,
            });
        }
    }
    current.regressions = found;
    current.verdict = verdict_of(
        &current.violations,
        &current.insufficient,
        &current.regressions,
    );
}
