use crate::model::{Action, Decision, LoopState, LoopView, Outcome, Policy, Totals};

pub const MAX_LOOPS: usize = 256;
pub const MAX_NAME: usize = 64;
pub const MAX_REASON: usize = 200;

#[derive(Debug, Clone)]
struct Entry {
    name: String,
    period: f64,
    state: LoopState,
    restarts: u64,
    stalls: u64,
    last_error: String,
    started: f64,
    beat: f64,
    delay: Option<f64>,
}

#[derive(Debug, Default)]
pub struct LoopBook {
    entries: Vec<Entry>,
}

#[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
fn seconds(value: f64) -> u64 {
    if value.is_finite() && value > 0.0 {
        value as u64
    } else {
        0
    }
}

fn clip(text: &str, limit: usize) -> String {
    text.chars().take(limit).collect()
}

impl LoopBook {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    fn entry(&mut self, name: &str) -> Option<&mut Entry> {
        self.entries.iter_mut().find(|e| e.name == name)
    }

    pub fn add(&mut self, name: &str, period: f64, now: f64) -> bool {
        let name = clip(name, MAX_NAME);
        let period = if period.is_finite() && period > 0.0 {
            period
        } else {
            0.0
        };
        if let Some(existing) = self.entry(&name) {
            existing.period = period;
            return true;
        }
        if self.entries.len() >= MAX_LOOPS || name.is_empty() {
            return false;
        }
        self.entries.push(Entry {
            name,
            period,
            state: LoopState::Starting,
            restarts: 0,
            stalls: 0,
            last_error: String::new(),
            started: 0.0,
            beat: now,
            delay: None,
        });
        true
    }

    pub fn start(&mut self, name: &str, now: f64) -> bool {
        self.entry(name).is_some_and(|e| {
            e.started = now;
            e.beat = now;
            e.state = LoopState::Running;
            true
        })
    }

    pub fn beat(&mut self, name: &str, now: f64) -> bool {
        self.entry(name).is_some_and(|e| {
            e.beat = now;
            true
        })
    }

    pub fn exit(
        &mut self,
        name: &str,
        outcome: Outcome,
        reason: &str,
        now: f64,
        policy: Policy,
    ) -> Option<Decision> {
        let policy = policy.sanitized();
        let entry = self.entry(name)?;
        if outcome == Outcome::Done {
            entry.state = LoopState::Done;
            return Some(Decision {
                action: Action::Finish,
                delay: 0.0,
                report: false,
                restarts: entry.restarts,
            });
        }
        entry.last_error = clip(reason, MAX_REASON);
        entry.restarts = entry.restarts.saturating_add(1);
        if !policy.restart_enabled {
            entry.state = LoopState::Halted;
            return Some(Decision {
                action: Action::Halt,
                delay: 0.0,
                report: true,
                restarts: entry.restarts,
            });
        }
        entry.state = LoopState::Restarting;
        let mut delay = entry.delay.unwrap_or(policy.backoff_min);
        if now - entry.started > policy.stable_after {
            delay = policy.backoff_min;
        }
        entry.delay = Some((delay * 2.0).min(policy.backoff_max));
        let report =
            entry.restarts == 1 || entry.restarts.checked_rem(policy.report_every) == Some(0);
        Some(Decision {
            action: Action::Restart,
            delay,
            report,
            restarts: entry.restarts,
        })
    }

    pub fn stalled(&mut self, now: f64, stale_factor: f64) -> Vec<String> {
        let factor = if stale_factor.is_finite() {
            stale_factor.clamp(1.0, 1000.0)
        } else {
            5.0
        };
        let mut out = Vec::new();
        for entry in &mut self.entries {
            if entry.state != LoopState::Running || entry.period <= 0.0 {
                continue;
            }
            if now - entry.beat > entry.period * factor {
                entry.stalls = entry.stalls.saturating_add(1);
                entry.beat = now;
                out.push(entry.name.clone());
            }
        }
        out
    }

    #[must_use]
    pub fn snapshot(&self, now: f64) -> Vec<LoopView> {
        self.entries
            .iter()
            .map(|e| LoopView {
                name: e.name.clone(),
                state: e.state.code(),
                restarts: e.restarts,
                stalls: e.stalls,
                last_error: e.last_error.clone(),
                up_s: if e.started > 0.0 {
                    seconds(now - e.started)
                } else {
                    0
                },
                heartbeat_s: (e.period > 0.0).then(|| seconds(now - e.beat)),
                period_s: (e.period > 0.0).then_some(e.period),
            })
            .collect()
    }

    #[must_use]
    pub fn totals(&self) -> Totals {
        Totals {
            loops: self.entries.len(),
            running: self
                .entries
                .iter()
                .filter(|e| e.state == LoopState::Running)
                .count(),
            restarts: self
                .entries
                .iter()
                .fold(0u64, |acc, e| acc.saturating_add(e.restarts)),
            stalls: self
                .entries
                .iter()
                .fold(0u64, |acc, e| acc.saturating_add(e.stalls)),
        }
    }
}
