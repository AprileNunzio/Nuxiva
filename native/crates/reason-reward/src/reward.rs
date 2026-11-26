use serde::Serialize;

use crate::error::RewardResult;
use crate::signal::{Signal, StepOutcome};

pub const SCORE_MAX: i32 = 10_000;
pub const SCORE_MIN: i32 = -10_000;
pub const GAIN_MAX: u32 = 10_000;
const HALF: i32 = 5_000;
const ISSUE_COST: u32 = 1_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct Reward {
    pub score_bps: i32,
    pub signals: u32,
    pub verified: bool,
    pub unsafe_action: bool,
}

impl Reward {
    #[must_use]
    pub fn gain(&self) -> u32 {
        let shifted = self.score_bps.saturating_sub(SCORE_MIN) / 2;
        u32::try_from(shifted.clamp(0, SCORE_MAX)).unwrap_or(0)
    }
}

fn ratio(passed: u32, total: u32) -> i32 {
    let scaled = u64::from(passed)
        .saturating_mul(20_000)
        .checked_div(u64::from(total))
        .unwrap_or(0);
    i32::try_from(scaled).unwrap_or(0).saturating_add(SCORE_MIN)
}

fn document(valid: bool, issues: u32) -> i32 {
    if !valid {
        return SCORE_MIN;
    }
    let cost = issues.saturating_mul(ISSUE_COST).min(GAIN_MAX);
    SCORE_MAX.saturating_sub(i32::try_from(cost).unwrap_or(SCORE_MAX))
}

fn step(outcome: StepOutcome) -> Option<i32> {
    match outcome {
        StepOutcome::Done | StepOutcome::Replayed => Some(SCORE_MAX),
        StepOutcome::Failed => Some(SCORE_MIN),
        StepOutcome::Indeterminate | StepOutcome::Missing => Some(-HALF),
        StepOutcome::Skipped | StepOutcome::Cancelled | StepOutcome::Denied => None,
    }
}

fn value(signal: &Signal) -> Option<i32> {
    match *signal {
        Signal::Tests { passed, total } => Some(ratio(passed, total)),
        Signal::Command {
            exit_code,
            timed_out,
        } => Some(if exit_code == 0 && !timed_out {
            SCORE_MAX
        } else {
            SCORE_MIN
        }),
        Signal::Document { valid, issues } => Some(document(valid, issues)),
        Signal::Step { outcome } => step(outcome),
        Signal::Intent {
            matched,
            completed,
            wrong_action,
        } => Some(match (wrong_action, completed, matched) {
            (true, _, _) | (false, false, _) => SCORE_MIN,
            (false, true, false) => -HALF,
            (false, true, true) => SCORE_MAX,
        }),
    }
}

pub fn score(signals: &[Signal]) -> RewardResult<Reward> {
    let mut total: i64 = 0;
    let mut counted: u32 = 0;
    let mut unsafe_action = false;
    for signal in signals {
        signal.validate()?;
        unsafe_action |= signal.is_unsafe();
        if let Some(points) = value(signal) {
            total = total.saturating_add(i64::from(points));
            counted = counted.saturating_add(1);
        }
    }
    let mean = total.checked_div(i64::from(counted)).unwrap_or(0);
    let bounded =
        i32::try_from(mean.clamp(i64::from(SCORE_MIN), i64::from(SCORE_MAX))).unwrap_or(0);
    Ok(Reward {
        score_bps: if unsafe_action { SCORE_MIN } else { bounded },
        signals: counted,
        verified: counted > 0,
        unsafe_action,
    })
}
