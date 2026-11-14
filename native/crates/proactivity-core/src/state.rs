use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};

use crate::engine::Engine;
use crate::error::{ProactivityError, ProactivityResult};
use crate::gate::PersonPolicy;
use crate::habit::Habit;
use crate::learn::Learner;
use crate::model::{Context, Forecast, Signal};
use crate::settings::MAX_PAYLOAD;

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct State {
    learner: Learner,
    habits: BTreeMap<String, Habit>,
    policies: BTreeMap<String, PersonPolicy>,
    approved: BTreeSet<String>,
}

impl Engine {
    pub fn export_state(&self) -> ProactivityResult<String> {
        serde_json::to_string(&State {
            learner: self.learner.clone(),
            habits: self.habits.clone(),
            policies: self.policies.clone(),
            approved: self.approved.clone(),
        })
        .map_err(|_| ProactivityError::Serialize)
    }

    pub fn import_state(&mut self, text: &str) -> ProactivityResult<()> {
        if text.len() > MAX_PAYLOAD {
            return Err(ProactivityError::TooLarge);
        }
        let state: State = serde_json::from_str(text).map_err(|_| ProactivityError::Parse)?;
        let rules = &self.rules.rules;
        let safe = state.approved.iter().all(|id| {
            rules.get(id).is_some_and(|r| {
                r.action.risk_max <= nuxiva_taskq_core::Risk::Low && r.action.undo.is_some()
            })
        });
        let habits_ok = state.habits.len() <= 4_096
            && state.habits.iter().all(|(k, h)| {
                h.valid()
                    && k.split_once('|')
                        .is_some_and(|(rule, _)| rules.get(rule).is_some_and(|r| r.habit.is_some()))
            });
        if !safe || !habits_ok || !state.learner.valid() || state.policies.len() > 256 {
            return Err(ProactivityError::Invalid);
        }
        self.learner = state.learner;
        self.habits = state.habits;
        self.policies = state.policies;
        self.approved = state.approved;
        Ok(())
    }

    pub fn signal_from_json(text: &str) -> ProactivityResult<Signal> {
        if text.len() > 8 * 1024 {
            return Err(ProactivityError::TooLarge);
        }
        serde_json::from_str(text).map_err(|_| ProactivityError::Parse)
    }

    pub fn context_from_json(text: &str) -> ProactivityResult<Context> {
        if text.len() > 8 * 1024 {
            return Err(ProactivityError::TooLarge);
        }
        let ctx: Context = serde_json::from_str(text).map_err(|_| ProactivityError::Parse)?;
        if ctx.valid() {
            Ok(ctx)
        } else {
            Err(ProactivityError::Invalid)
        }
    }

    pub fn policy_from_json(text: &str) -> ProactivityResult<PersonPolicy> {
        if text.len() > 8 * 1024 {
            return Err(ProactivityError::TooLarge);
        }
        serde_json::from_str(text).map_err(|_| ProactivityError::Parse)
    }

    pub fn forecast_from_json(text: &str) -> ProactivityResult<Forecast> {
        if text.len() > 8 * 1024 {
            return Err(ProactivityError::TooLarge);
        }
        serde_json::from_str(text).map_err(|_| ProactivityError::Parse)
    }
}
