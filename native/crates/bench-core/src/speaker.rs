use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::scene::{Background, Class};
use crate::stats::ratio;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SpeakerTrial {
    pub truth: Class,
    pub predicted: Class,
    pub truth_slot: Option<u16>,
    pub predicted_slot: Option<u16>,
    pub background: Background,
}

impl SpeakerTrial {
    fn correct_known(&self) -> bool {
        self.truth == Class::Known
            && self.predicted == Class::Known
            && self.truth_slot == self.predicted_slot
    }
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SpeakerReport {
    pub trials: u64,
    pub known_trials: u64,
    pub guest_trials: u64,
    pub broadcast_trials: u64,
    pub background_trials: u64,
    pub confusion: BTreeMap<String, u64>,
    pub known_miss_rate: f64,
    pub false_known_rate: f64,
    pub guest_as_known_rate: f64,
    pub broadcast_as_known_rate: f64,
    pub background_false_known_rate: f64,
    pub background_known_miss_rate: f64,
}

pub fn analyze(trials: &[SpeakerTrial]) -> SpeakerReport {
    let mut r = SpeakerReport::default();
    let classes = [Class::Known, Class::Guest, Class::Broadcast];
    for truth in classes {
        for predicted in classes {
            r.confusion
                .insert(format!("{}>{}", truth.name(), predicted.name()), 0);
        }
    }
    let (mut predicted_known, mut false_known) = (0u64, 0u64);
    let (mut known_wrong, mut guest_known, mut broadcast_known) = (0u64, 0u64, 0u64);
    let (mut bg_nonknown, mut bg_false_known) = (0u64, 0u64);
    let (mut bg_known, mut bg_known_wrong) = (0u64, 0u64);
    for t in trials {
        r.trials = r.trials.saturating_add(1);
        let key = format!("{}>{}", t.truth.name(), t.predicted.name());
        if let Some(count) = r.confusion.get_mut(&key) {
            *count = count.saturating_add(1);
        }
        if t.background.is_noisy() {
            r.background_trials = r.background_trials.saturating_add(1);
        }
        if t.predicted == Class::Known {
            predicted_known = predicted_known.saturating_add(1);
            if !t.correct_known() {
                false_known = false_known.saturating_add(1);
            }
        }
        match t.truth {
            Class::Known => {
                r.known_trials = r.known_trials.saturating_add(1);
                if !t.correct_known() {
                    known_wrong = known_wrong.saturating_add(1);
                }
                if t.background.is_noisy() {
                    bg_known = bg_known.saturating_add(1);
                    if !t.correct_known() {
                        bg_known_wrong = bg_known_wrong.saturating_add(1);
                    }
                }
            }
            Class::Guest => {
                r.guest_trials = r.guest_trials.saturating_add(1);
                if t.predicted == Class::Known {
                    guest_known = guest_known.saturating_add(1);
                }
            }
            Class::Broadcast => {
                r.broadcast_trials = r.broadcast_trials.saturating_add(1);
                if t.predicted == Class::Known {
                    broadcast_known = broadcast_known.saturating_add(1);
                }
            }
        }
        if t.background.is_noisy() && t.truth != Class::Known {
            bg_nonknown = bg_nonknown.saturating_add(1);
            if t.predicted == Class::Known {
                bg_false_known = bg_false_known.saturating_add(1);
            }
        }
    }
    r.known_miss_rate = ratio(known_wrong, r.known_trials);
    r.false_known_rate = ratio(false_known, predicted_known);
    r.guest_as_known_rate = ratio(guest_known, r.guest_trials);
    r.broadcast_as_known_rate = ratio(broadcast_known, r.broadcast_trials);
    r.background_false_known_rate = ratio(bg_false_known, bg_nonknown);
    r.background_known_miss_rate = ratio(bg_known_wrong, bg_known);
    r
}
