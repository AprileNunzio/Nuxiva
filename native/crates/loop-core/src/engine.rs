use serde::Serialize;

use crate::error::{LoopError, LoopResult};
use crate::judge::judge;
use crate::redact::redact;
use crate::settings::Settings;
use crate::wire::{Artifact, ArtifactDraft, CriticReport, Feedback, Verdict};

pub trait Coder {
    fn produce(&mut self, feedback: Option<&Feedback>, iteration: u32)
    -> LoopResult<ArtifactDraft>;
}

pub trait Critic {
    fn evaluate(&mut self, artifact: &Artifact, iteration: u32) -> LoopResult<CriticReport>;
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Escalation {
    RepeatedFailure,
    Inconclusive,
    PolicyViolation,
    CoderFailed,
    CriticFailed,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case", tag = "outcome")]
pub enum Outcome {
    Passed {
        artifact: Artifact,
        report: CriticReport,
        iterations: u32,
    },
    Escalated {
        reason: Escalation,
        fingerprint: Option<String>,
        iterations: u32,
    },
    Exhausted {
        iterations: u32,
        fingerprint: Option<String>,
    },
}

pub fn run(
    settings: &Settings,
    coder: &mut dyn Coder,
    critic: &mut dyn Critic,
) -> LoopResult<Outcome> {
    settings.validate()?;
    let mut feedback: Option<Feedback> = None;
    let mut last: Option<String> = None;
    let mut repeats = 0u32;
    let mut inconclusive = 0u32;
    let mut iteration = 0u32;
    while iteration < settings.max_iterations {
        iteration = iteration.saturating_add(1);
        let Ok(draft) = coder.produce(feedback.as_ref(), iteration) else {
            return Ok(Outcome::Escalated {
                reason: Escalation::CoderFailed,
                fingerprint: last,
                iterations: iteration,
            });
        };
        let artifact = match Artifact::seal(draft, settings) {
            Ok(a) => a,
            Err(LoopError::Protected | LoopError::Path) => {
                return Ok(Outcome::Escalated {
                    reason: Escalation::PolicyViolation,
                    fingerprint: last,
                    iterations: iteration,
                });
            }
            Err(_) => {
                return Ok(Outcome::Escalated {
                    reason: Escalation::CoderFailed,
                    fingerprint: last,
                    iterations: iteration,
                });
            }
        };
        let Ok(report) = critic.evaluate(&artifact, iteration) else {
            return Ok(Outcome::Escalated {
                reason: Escalation::CriticFailed,
                fingerprint: last,
                iterations: iteration,
            });
        };
        let Ok(verdict) = judge(&report, &artifact, iteration, settings) else {
            return Ok(Outcome::Escalated {
                reason: Escalation::CriticFailed,
                fingerprint: last,
                iterations: iteration,
            });
        };
        match verdict.verdict {
            Verdict::Pass => {
                return Ok(Outcome::Passed {
                    artifact,
                    report,
                    iterations: iteration,
                });
            }
            Verdict::Inconclusive => {
                inconclusive = inconclusive.saturating_add(1);
                if inconclusive >= settings.inconclusive_max {
                    return Ok(Outcome::Escalated {
                        reason: Escalation::Inconclusive,
                        fingerprint: last,
                        iterations: iteration,
                    });
                }
            }
            Verdict::Fail => {
                inconclusive = 0;
                repeats = if last.as_deref() == Some(verdict.fingerprint.as_str()) {
                    repeats.saturating_add(1)
                } else {
                    1
                };
                last = Some(verdict.fingerprint.clone());
                if repeats >= settings.repeat_escalate {
                    return Ok(Outcome::Escalated {
                        reason: Escalation::RepeatedFailure,
                        fingerprint: last,
                        iterations: iteration,
                    });
                }
                let mut joined = String::new();
                for c in report.checks.iter().filter(|c| !c.passed) {
                    joined.push('[');
                    joined.push_str(&c.name);
                    joined.push_str("]\n");
                    joined.push_str(&c.log);
                    joined.push('\n');
                }
                feedback = Some(Feedback {
                    iteration,
                    failed: verdict.failed,
                    untrusted_log: redact(&joined, settings.log_chars),
                });
            }
        }
    }
    Ok(Outcome::Exhausted {
        iterations: iteration,
        fingerprint: last,
    })
}
