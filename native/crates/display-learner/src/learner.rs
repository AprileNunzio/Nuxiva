use std::collections::{BTreeMap, BTreeSet};

use nuxiva_display_planner::{Size, category_of};
use serde::{Deserialize, Serialize};

use crate::context::{ContextVector, ScreenRole};
use crate::error::LearnError;
use crate::guard::{explorable, learnable};
use crate::policy::LearnerPolicy;
use crate::profile::{Metrics, Profile};
use crate::signal::{FeedbackSample, Kind, valid_person, valid_widget};

const SCALE: u64 = 10_000;
pub const MAX_PROFILE_BYTES: usize = 2 * 1024 * 1024;

#[derive(Debug, Clone, Copy, PartialEq, Default, Serialize, Deserialize)]
pub struct Affinity {
    pub value: f32,
    pub mean: f32,
    pub evidence: f32,
    pub explored: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Outcome {
    Learned,
    Counted,
    Ignored,
}

#[derive(Debug, Default)]
pub struct Learner {
    policy: LearnerPolicy,
    persons: BTreeMap<String, Profile>,
    session: Profile,
    dirty: BTreeSet<String>,
}

fn place_key(widget: &str, role: ScreenRole) -> String {
    format!("{widget}|{}", role.index())
}

fn mix(person: &str, widget: &str, tick: u64) -> u64 {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    for b in person
        .bytes()
        .chain([0])
        .chain(widget.bytes())
        .chain(tick.to_le_bytes())
    {
        h ^= u64::from(b);
        h = h.wrapping_mul(0x0100_0000_01b3);
    }
    h
}

impl Learner {
    pub fn new(policy: LearnerPolicy) -> Result<Self, LearnError> {
        policy.validate()?;
        Ok(Self {
            policy,
            ..Self::default()
        })
    }

    #[must_use]
    pub const fn policy(&self) -> &LearnerPolicy {
        &self.policy
    }

    fn profile_mut(
        &mut self,
        person: Option<&str>,
        guests: bool,
    ) -> Result<&mut Profile, LearnError> {
        match person {
            Some(key) if !guests => {
                if !self.persons.contains_key(key) && self.persons.len() >= self.policy.max_persons
                {
                    return Err(LearnError::Capacity);
                }
                self.dirty.insert(key.to_owned());
                Ok(self.persons.entry(key.to_owned()).or_default())
            }
            _ => Ok(&mut self.session),
        }
    }

    pub fn observe(&mut self, s: &FeedbackSample) -> Result<Outcome, LearnError> {
        s.validate()?;
        if !learnable(category_of(&s.widget), s.urgency) {
            return Ok(Outcome::Ignored);
        }
        let policy = self.policy;
        let profile = self.profile_mut(s.person.as_deref(), s.guests)?;
        profile.metrics.count(s.kind, s.at_ms, &policy);
        let (reward, weight) = s.kind.reward();
        let mut outcome = Outcome::Counted;
        if weight > 0.0 {
            if !profile.models.contains_key(&s.widget) {
                profile.evict_models(policy.max_models.saturating_sub(1));
            }
            profile
                .models
                .entry(s.widget.clone())
                .or_default()
                .observe(&s.context, reward, weight, s.at_ms, &policy);
            outcome = Outcome::Learned;
        }
        if matches!(s.kind, Kind::Move | Kind::Resize) && (s.cell.is_some() || s.size.is_some()) {
            let key = place_key(&s.widget, s.context.role);
            if !profile.places.contains_key(&key) && profile.places.len() >= policy.max_places {
                if let Some(first) = profile.places.keys().next().cloned() {
                    profile.places.remove(&first);
                }
            }
            profile
                .places
                .entry(key)
                .or_default()
                .observe(s.cell, s.size, s.at_ms, &policy);
            outcome = Outcome::Learned;
        }
        Ok(outcome)
    }

    fn profile(&self, person: Option<&str>, guests: bool) -> Option<&Profile> {
        match person {
            Some(key) if !guests => self.persons.get(key),
            _ => Some(&self.session),
        }
    }

    #[must_use]
    pub fn affinity(
        &self,
        person: Option<&str>,
        widget: &str,
        ctx: &ContextVector,
        now_ms: u64,
        tick: u64,
        guests: bool,
    ) -> Affinity {
        let category = category_of(widget);
        if !learnable(category, 0) {
            return Affinity::default();
        }
        let Some(model) = self
            .profile(person, guests)
            .and_then(|p| p.models.get(widget))
        else {
            return Affinity::default();
        };
        let est = model.estimate(ctx, now_ms, &self.policy);
        let limit = self.policy.limit;
        let mut value = est.mean * limit;
        let threshold = (f64::from(self.policy.explore_rate) * 10_000.0).round();
        #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
        let threshold = threshold.clamp(0.0, 10_000.0) as u64;
        let explored = !guests
            && explorable(category)
            && person.is_some_and(|p| mix(p, widget, tick) % SCALE < threshold);
        if explored {
            value += self.policy.explore_bonus * est.uncertainty();
        }
        Affinity {
            value: value.clamp(-limit, limit),
            mean: est.mean,
            evidence: est.evidence,
            explored,
        }
    }

    #[must_use]
    pub fn placement(
        &self,
        person: Option<&str>,
        widget: &str,
        role: ScreenRole,
        now_ms: u64,
    ) -> (Option<[u8; 2]>, Option<Size>) {
        self.profile(person, false)
            .and_then(|p| p.places.get(&place_key(widget, role)))
            .map_or((None, None), |pl| {
                (pl.cell(now_ms, &self.policy), pl.size(now_ms, &self.policy))
            })
    }

    #[must_use]
    pub fn metrics(&self, person: Option<&str>) -> Option<Metrics> {
        self.profile(person, false).map(|p| p.metrics)
    }

    pub fn reset(&mut self, person: &str) -> Result<bool, LearnError> {
        valid_person(person)?;
        self.dirty.remove(person);
        Ok(self.persons.remove(person).is_some())
    }

    pub fn forget_session(&mut self) {
        self.session = Profile::default();
    }

    pub fn take_dirty(&mut self) -> Vec<String> {
        std::mem::take(&mut self.dirty).into_iter().collect()
    }

    #[must_use]
    pub fn persons(&self) -> Vec<String> {
        self.persons.keys().cloned().collect()
    }

    pub fn export(&self, person: &str) -> Result<Vec<u8>, LearnError> {
        valid_person(person)?;
        let profile = self.persons.get(person).cloned().unwrap_or_default();
        serde_json::to_vec(&profile).map_err(|_| LearnError::Corrupt)
    }

    pub fn import(&mut self, person: &str, raw: &[u8]) -> Result<(), LearnError> {
        valid_person(person)?;
        if raw.len() > MAX_PROFILE_BYTES {
            return Err(LearnError::Corrupt);
        }
        let profile: Profile = serde_json::from_slice(raw).map_err(|_| LearnError::Corrupt)?;
        if !profile.sane(&self.policy) || profile.models.keys().any(|w| valid_widget(w).is_err()) {
            return Err(LearnError::Corrupt);
        }
        if !self.persons.contains_key(person) && self.persons.len() >= self.policy.max_persons {
            return Err(LearnError::Capacity);
        }
        self.persons.insert(person.to_owned(), profile);
        Ok(())
    }
}
