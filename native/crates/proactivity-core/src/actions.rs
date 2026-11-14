use nuxiva_taskq_core::{Risk, TaskSpec};

use crate::engine::Engine;
use crate::error::{ProactivityError, ProactivityResult};
use crate::gate::PersonPolicy;
use crate::learn::{Feedback, key};
use crate::model::person_ok;

impl Engine {
    pub fn accept(&mut self, id: u64, now: u64) -> ProactivityResult<TaskSpec> {
        let at = self
            .pending
            .iter()
            .position(|d| d.id == id)
            .ok_or(ProactivityError::NotFound)?;
        if self.pending.get(at).is_some_and(|d| d.action.is_none()) {
            return Err(ProactivityError::State);
        }
        let decision = self.pending.remove(at).ok_or(ProactivityError::NotFound)?;
        let k = key(&decision.rule, decision.person.as_deref());
        if decision.expires_at <= now {
            self.stats.expired = self.stats.expired.saturating_add(1);
            self.learner
                .feedback(&k, Feedback::Ignored, now, self.settings.mute_ms);
            return Err(ProactivityError::Expired);
        }
        let task = decision.action.clone().ok_or(ProactivityError::State)?;
        self.stats.accepted = self.stats.accepted.saturating_add(1);
        self.learner
            .feedback(&k, Feedback::Accepted, now, self.settings.mute_ms);
        self.register_undo(&decision, now);
        Ok(task)
    }

    pub fn refuse(&mut self, id: u64, now: u64) -> ProactivityResult<()> {
        let at = self
            .pending
            .iter()
            .position(|d| d.id == id)
            .ok_or(ProactivityError::NotFound)?;
        let decision = self.pending.remove(at).ok_or(ProactivityError::NotFound)?;
        let k = key(&decision.rule, decision.person.as_deref());
        self.learner
            .feedback(&k, Feedback::Refused, now, self.settings.mute_ms);
        self.stats.refused = self.stats.refused.saturating_add(1);
        Ok(())
    }

    pub fn dismiss(&mut self, id: u64) -> ProactivityResult<()> {
        let at = self
            .pending
            .iter()
            .position(|d| d.id == id)
            .ok_or(ProactivityError::NotFound)?;
        self.pending.remove(at);
        Ok(())
    }

    pub fn undo(&mut self, id: u64, now: u64) -> ProactivityResult<TaskSpec> {
        let at = self
            .undo
            .iter()
            .position(|u| u.id == id)
            .ok_or(ProactivityError::NotFound)?;
        let entry = self.undo.remove(at).ok_or(ProactivityError::NotFound)?;
        if entry.expires_at <= now {
            return Err(ProactivityError::Expired);
        }
        let k = key(&entry.rule, entry.person.as_deref());
        self.learner
            .feedback(&k, Feedback::Undone, now, self.settings.mute_ms);
        self.stats.undone = self.stats.undone.saturating_add(1);
        Ok(entry.task)
    }

    pub fn approve_always(&mut self, rule: &str) -> ProactivityResult<()> {
        let found = self
            .rules
            .rules
            .get(rule)
            .ok_or(ProactivityError::NotFound)?;
        if found.action.risk_max > Risk::Low || found.action.undo.is_none() {
            return Err(ProactivityError::Consent);
        }
        self.approved.insert(rule.to_owned());
        Ok(())
    }

    pub fn revoke(&mut self, rule: &str) {
        self.approved.remove(rule);
    }

    pub fn set_policy(&mut self, person: &str, policy: PersonPolicy) -> ProactivityResult<()> {
        if !person_ok(person) || (self.policies.len() >= 256 && !self.policies.contains_key(person))
        {
            return Err(ProactivityError::Invalid);
        }
        self.policies.insert(person.to_owned(), policy);
        Ok(())
    }

    pub fn reset_learning(&mut self, rule: &str, person: Option<&str>) {
        self.learner.clear_mute(&key(rule, person));
    }
}
