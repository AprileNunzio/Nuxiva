use std::collections::BTreeSet;

use sha2::{Digest, Sha256};

use crate::error::{LoopError, LoopResult};
use crate::redact::normalize_for_fingerprint;
use crate::settings::Settings;
use crate::wire::{Artifact, CriticReport, SCHEMA_VERSION, Verdict, hex};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Judgement {
    pub verdict: Verdict,
    pub failed: Vec<String>,
    pub fingerprint: String,
}

fn run_ok(text: &str) -> bool {
    !text.is_empty()
        && text.len() <= 128
        && text
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'_' | b':' | b'-'))
}

pub fn judge(
    report: &CriticReport,
    artifact: &Artifact,
    iteration: u32,
    settings: &Settings,
) -> LoopResult<Judgement> {
    if report.schema_version != SCHEMA_VERSION {
        return Err(LoopError::Version);
    }
    if report.digest != artifact.digest {
        return Err(LoopError::Digest);
    }
    if report.iteration != iteration || !run_ok(&report.sandbox_run) {
        return Err(LoopError::Report);
    }
    if report.checks.is_empty() || report.checks.len() > 64 {
        return Err(LoopError::Report);
    }
    let mut names = BTreeSet::new();
    for check in &report.checks {
        let valid = !check.name.is_empty()
            && check.name.len() <= 64
            && check.name.bytes().all(|b| {
                b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'.' | b'_' | b'-')
            });
        if !valid || !names.insert(check.name.as_str()) {
            return Err(LoopError::Report);
        }
    }
    let mut failed: Vec<String> = report
        .checks
        .iter()
        .filter(|c| !c.passed)
        .map(|c| c.name.clone())
        .collect();
    for required in &settings.required_checks {
        if !names.contains(required.as_str()) {
            failed.push(format!("missing.{required}"));
        }
    }
    failed.sort();
    let verdict = if report.verdict == Verdict::Inconclusive {
        Verdict::Inconclusive
    } else if failed.is_empty() {
        Verdict::Pass
    } else {
        Verdict::Fail
    };
    Ok(Judgement {
        verdict,
        fingerprint: fingerprint(report, &failed),
        failed,
    })
}

fn fingerprint(report: &CriticReport, failed: &[String]) -> String {
    let mut hasher = Sha256::new();
    for name in failed {
        hasher.update(name.as_bytes());
        hasher.update([0]);
        if let Some(check) = report.checks.iter().find(|c| &c.name == name) {
            hasher.update(normalize_for_fingerprint(&check.log).as_bytes());
        }
        hasher.update([1]);
    }
    hex(&hasher.finalize())
}
