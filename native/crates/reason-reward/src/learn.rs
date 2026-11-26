use model_router::{Profile, Task};
use serde::Serialize;

use crate::error::RewardResult;
use crate::ledger::{Key, Ledger};
use crate::reward::{Reward, score};
use crate::signal::Signal;

pub const MIN_TRIALS: u32 = 20;
pub const MAX_STEP_BPS: u16 = 300;
pub const MIN_CHANGE_BPS: u16 = 50;
pub const UNSAFE_PER_MILLE: u32 = 20;

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Adjustment {
    pub key: Key,
    pub current_bps: u16,
    pub proposed_bps: u16,
    pub evidence: u32,
    pub quarantine: bool,
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Learner {
    ledger: Ledger,
}

fn step_towards(current: u16, target: u16) -> u16 {
    if target >= current {
        current.saturating_add((target.saturating_sub(current)).min(MAX_STEP_BPS))
    } else {
        current.saturating_sub((current.saturating_sub(target)).min(MAX_STEP_BPS))
    }
}

impl Learner {
    #[must_use]
    pub fn new(ledger: Ledger) -> Self {
        Self { ledger }
    }

    #[must_use]
    pub fn ledger(&self) -> &Ledger {
        &self.ledger
    }

    pub fn observe(&mut self, key: &Key, signals: &[Signal]) -> RewardResult<Reward> {
        let reward = score(signals)?;
        self.ledger.record(key, &reward)?;
        Ok(reward)
    }

    pub fn propose<F>(&self, current: F) -> Vec<Adjustment>
    where
        F: Fn(&Key) -> Option<u16>,
    {
        self.ledger
            .iter()
            .filter(|(_, tally)| tally.trials >= MIN_TRIALS)
            .filter_map(|(key, tally)| {
                let now = current(key)?;
                let quarantine = tally.unsafe_per_mille() > UNSAFE_PER_MILLE;
                let proposed = if quarantine {
                    0
                } else {
                    step_towards(now, tally.lower_bound_bps())
                };
                let moved = now.abs_diff(proposed);
                (quarantine || moved >= MIN_CHANGE_BPS).then(|| Adjustment {
                    key: key.clone(),
                    current_bps: now,
                    proposed_bps: proposed,
                    evidence: tally.trials,
                    quarantine,
                })
            })
            .collect()
    }
}

pub fn apply(profile: &mut Profile, task: Task, adjustment: &Adjustment) -> RewardResult<()> {
    let mut next = profile.clone();
    next.quality_bps.insert(task, adjustment.proposed_bps);
    next.validate()
        .map_err(|_| crate::error::RewardError::Invalid("profile"))?;
    *profile = next;
    Ok(())
}
