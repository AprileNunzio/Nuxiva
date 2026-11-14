use std::collections::{BTreeMap, VecDeque};

use serde::{Deserialize, Serialize};

use crate::catalog::Catalog;
use crate::error::{ReflectError, ReflectResult};
use crate::settings::{MAX_PAYLOAD, Settings};
use crate::wire::{Delta, Lesson, LessonState, Reflection, SCHEMA_VERSION};

const CODE_QUEUE: usize = 64;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Sample {
    score: u32,
    observed: Vec<(String, String)>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Blocked {
    kind: String,
    value: String,
    until: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Snapshot {
    schema_version: u32,
    next_id: u64,
    history: Vec<Sample>,
    lessons: Vec<Lesson>,
    previous: BTreeMap<String, Vec<Lesson>>,
    blocked: Vec<Blocked>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Verification {
    pub treated: usize,
    pub treated_mean: u32,
    pub baseline_mean: u32,
    pub passed: bool,
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Recorded {
    pub candidate: Option<u64>,
    pub adopted: Vec<u64>,
    pub blocked: bool,
    pub code_request: Option<String>,
}

#[derive(Debug)]
pub struct Store {
    settings: Settings,
    catalog: Catalog,
    history: VecDeque<Sample>,
    lessons: BTreeMap<u64, Lesson>,
    previous: BTreeMap<String, Vec<Lesson>>,
    blocked: Vec<Blocked>,
    code: VecDeque<String>,
    next_id: u64,
}

fn mean(total: u64, count: usize) -> u32 {
    u32::try_from(
        total
            .checked_div(u64::try_from(count).unwrap_or(u64::MAX))
            .unwrap_or(0),
    )
    .unwrap_or(u32::MAX)
}

impl Store {
    pub fn new(settings: Settings, catalog: Catalog) -> ReflectResult<Self> {
        settings.validate()?;
        catalog.validate()?;
        Ok(Self {
            settings,
            catalog,
            history: VecDeque::new(),
            lessons: BTreeMap::new(),
            previous: BTreeMap::new(),
            blocked: Vec::new(),
            code: VecDeque::new(),
            next_id: 1,
        })
    }

    #[must_use]
    pub fn verify(&self, lesson: &Lesson) -> Verification {
        let (mut t_total, mut t_count, mut b_total, mut b_count) = (0u64, 0usize, 0u64, 0usize);
        for sample in &self.history {
            let treated = sample
                .observed
                .iter()
                .any(|(k, v)| *k == lesson.kind && *v == lesson.value);
            if treated {
                t_total = t_total.saturating_add(u64::from(sample.score));
                t_count = t_count.saturating_add(1);
            } else {
                b_total = b_total.saturating_add(u64::from(sample.score));
                b_count = b_count.saturating_add(1);
            }
        }
        let (treated_mean, baseline_mean) = (mean(t_total, t_count), mean(b_total, b_count));
        let passed = t_count >= self.settings.min_samples
            && b_count > 0
            && treated_mean >= baseline_mean.saturating_add(self.settings.margin_permille);
        Verification {
            treated: t_count,
            treated_mean,
            baseline_mean,
            passed,
        }
    }

    fn is_blocked(&self, kind: &str, value: &str, now: u64) -> bool {
        self.blocked
            .iter()
            .any(|b| b.kind == kind && b.value == value && b.until > now)
    }

    pub fn record(&mut self, reflection: &Reflection, now: u64) -> ReflectResult<Recorded> {
        reflection.validate(&self.catalog)?;
        if self.history.len() >= self.settings.history_cap {
            self.history.pop_front();
        }
        self.history.push_back(Sample {
            score: reflection.score(&self.settings),
            observed: reflection
                .observed
                .iter()
                .map(|o| (o.kind.clone(), o.value.clone()))
                .collect(),
        });
        let mut out = Recorded::default();
        match &reflection.proposed {
            Some(Delta::Data { candidate }) => {
                if self.is_blocked(&candidate.kind, &candidate.value, now) {
                    out.blocked = true;
                } else {
                    out.candidate = Some(self.propose(&candidate.kind, &candidate.value, now)?);
                }
            }
            Some(Delta::Code { request_ref }) => {
                if self.code.len() >= CODE_QUEUE {
                    self.code.pop_front();
                }
                self.code.push_back(request_ref.clone());
                out.code_request = Some(request_ref.clone());
            }
            None => {}
        }
        let pending: Vec<u64> = self
            .lessons
            .values()
            .filter(|l| l.state == LessonState::Candidate)
            .map(|l| l.id)
            .collect();
        for id in pending {
            if self.try_adopt(id, now).is_ok() {
                out.adopted.push(id);
            }
        }
        self.maintain(now);
        Ok(out)
    }

    fn propose(&mut self, kind: &str, value: &str, now: u64) -> ReflectResult<u64> {
        let spec = self.catalog.check(kind, value)?.clone();
        if let Some(existing) = self.lessons.values_mut().find(|l| {
            l.kind == kind
                && l.value == value
                && matches!(l.state, LessonState::Candidate | LessonState::Adopted)
        }) {
            existing.evidence = existing.evidence.saturating_add(1);
            existing.confirmed_at = now;
            return Ok(existing.id);
        }
        let id = self.next_id;
        self.next_id = self.next_id.saturating_add(1);
        self.lessons.insert(
            id,
            Lesson {
                id,
                kind: kind.to_owned(),
                domain: spec.domain,
                value: value.to_owned(),
                state: LessonState::Candidate,
                version: 0,
                evidence: 1,
                user_confirmed: false,
                created_at: now,
                confirmed_at: now,
            },
        );
        Ok(id)
    }

    fn adopt(&mut self, id: u64, now: u64) -> ReflectResult<()> {
        let kind = self
            .lessons
            .get(&id)
            .ok_or(ReflectError::NotFound)?
            .kind
            .clone();
        let current = self
            .lessons
            .values()
            .find(|l| l.kind == kind && l.state == LessonState::Adopted && l.id != id)
            .map(|l| l.id);
        let version = self
            .previous
            .get(&kind)
            .map_or(0, |p| u32::try_from(p.len()).unwrap_or(u32::MAX))
            .saturating_add(1);
        if let Some(old) = current {
            if let Some(lesson) = self.lessons.get_mut(&old) {
                lesson.state = LessonState::Expired;
                self.previous
                    .entry(kind.clone())
                    .or_default()
                    .push(lesson.clone());
            }
        }
        let lesson = self.lessons.get_mut(&id).ok_or(ReflectError::NotFound)?;
        lesson.state = LessonState::Adopted;
        lesson.version = version;
        lesson.confirmed_at = now;
        Ok(())
    }

    pub fn try_adopt(&mut self, id: u64, now: u64) -> ReflectResult<Verification> {
        let lesson = self.lessons.get(&id).ok_or(ReflectError::NotFound)?.clone();
        if lesson.state != LessonState::Candidate {
            return Err(ReflectError::State);
        }
        let check = self.verify(&lesson);
        if !check.passed {
            return Err(ReflectError::State);
        }
        self.adopt(id, now)?;
        Ok(check)
    }

    pub fn confirm(&mut self, id: u64, now: u64) -> ReflectResult<()> {
        let lesson = self.lessons.get_mut(&id).ok_or(ReflectError::NotFound)?;
        match lesson.state {
            LessonState::Adopted => {
                lesson.user_confirmed = true;
                lesson.confirmed_at = now;
                Ok(())
            }
            LessonState::Candidate => {
                lesson.user_confirmed = true;
                let (kind, value) = (lesson.kind.clone(), lesson.value.clone());
                if self.is_blocked(&kind, &value, now) {
                    return Err(ReflectError::Blocked);
                }
                self.adopt(id, now)
            }
            _ => Err(ReflectError::State),
        }
    }

    pub fn reject(&mut self, id: u64, now: u64) -> ReflectResult<()> {
        let lesson = self.lessons.get_mut(&id).ok_or(ReflectError::NotFound)?;
        if matches!(lesson.state, LessonState::Rejected | LessonState::Expired) {
            return Err(ReflectError::State);
        }
        let was_adopted = lesson.state == LessonState::Adopted;
        lesson.state = LessonState::Rejected;
        let blocked = Blocked {
            kind: lesson.kind.clone(),
            value: lesson.value.clone(),
            until: now.saturating_add(self.settings.block_ms),
        };
        let kind = lesson.kind.clone();
        self.blocked.push(blocked);
        if was_adopted {
            self.restore_previous(&kind, now);
        }
        Ok(())
    }

    pub fn revert(&mut self, kind: &str, now: u64) -> ReflectResult<()> {
        let id = self
            .lessons
            .values()
            .find(|l| l.kind == kind && l.state == LessonState::Adopted)
            .map(|l| l.id)
            .ok_or(ReflectError::NotFound)?;
        if let Some(lesson) = self.lessons.get_mut(&id) {
            lesson.state = LessonState::Expired;
        }
        self.restore_previous(kind, now);
        Ok(())
    }

    fn restore_previous(&mut self, kind: &str, now: u64) {
        let Some(mut old) = self.previous.get_mut(kind).and_then(Vec::pop) else {
            return;
        };
        if let Some(live) = self.lessons.get_mut(&old.id) {
            live.state = LessonState::Adopted;
            live.confirmed_at = now;
        } else {
            old.state = LessonState::Adopted;
            self.lessons.insert(old.id, old);
        }
    }

    pub fn maintain(&mut self, now: u64) {
        self.blocked.retain(|b| b.until > now);
        let ttl = self.settings.ttl_ms;
        let stale: Vec<u64> = self
            .lessons
            .values()
            .filter(|l| {
                l.state == LessonState::Candidate
                    && !l.user_confirmed
                    && now.saturating_sub(l.confirmed_at) > ttl
            })
            .map(|l| l.id)
            .collect();
        for id in stale {
            if let Some(l) = self.lessons.get_mut(&id) {
                l.state = LessonState::Expired;
            }
        }
        let regress: Vec<(u64, String)> = self
            .lessons
            .values()
            .filter(|l| l.state == LessonState::Adopted && !l.user_confirmed)
            .filter(|l| {
                let v = self.verify(l);
                v.treated >= self.settings.min_samples && v.treated_mean < v.baseline_mean
            })
            .map(|l| (l.id, l.kind.clone()))
            .collect();
        for (id, kind) in regress {
            if let Some(l) = self.lessons.get_mut(&id) {
                l.state = LessonState::Expired;
            }
            self.restore_previous(&kind, now);
        }
        self.enforce_cap();
        self.lessons.retain(|_, l| {
            !matches!(l.state, LessonState::Expired | LessonState::Rejected)
                || now.saturating_sub(l.confirmed_at) <= ttl
        });
    }

    fn enforce_cap(&mut self) {
        let mut by_domain: BTreeMap<String, Vec<(u64, u64, bool)>> = BTreeMap::new();
        for l in self
            .lessons
            .values()
            .filter(|l| matches!(l.state, LessonState::Candidate | LessonState::Adopted))
        {
            by_domain.entry(l.domain.clone()).or_default().push((
                l.id,
                l.confirmed_at,
                l.state == LessonState::Adopted,
            ));
        }
        for (_, mut list) in by_domain {
            if list.len() <= self.settings.domain_cap {
                continue;
            }
            list.sort_by_key(|(id, at, adopted)| (*adopted, *at, *id));
            let drop = list.len().saturating_sub(self.settings.domain_cap);
            for (id, _, _) in list.into_iter().take(drop) {
                if let Some(l) = self.lessons.get_mut(&id) {
                    l.state = LessonState::Expired;
                }
            }
        }
    }

    #[must_use]
    pub fn lesson_for(&self, kind: &str) -> Option<&Lesson> {
        self.lessons
            .values()
            .find(|l| l.kind == kind && l.state == LessonState::Adopted)
    }

    #[must_use]
    pub fn lessons(&self, state: LessonState) -> Vec<&Lesson> {
        self.lessons.values().filter(|l| l.state == state).collect()
    }

    pub fn take_code_requests(&mut self) -> Vec<String> {
        self.code.drain(..).collect()
    }

    #[must_use]
    pub fn history_len(&self) -> usize {
        self.history.len()
    }

    pub fn export(&self) -> ReflectResult<String> {
        let snap = Snapshot {
            schema_version: SCHEMA_VERSION,
            next_id: self.next_id,
            history: self.history.iter().cloned().collect(),
            lessons: self.lessons.values().cloned().collect(),
            previous: self.previous.clone(),
            blocked: self.blocked.clone(),
        };
        serde_json::to_string(&snap).map_err(|_| ReflectError::Serialize)
    }

    pub fn import(settings: Settings, catalog: Catalog, text: &str) -> ReflectResult<Self> {
        if text.len() > MAX_PAYLOAD {
            return Err(ReflectError::TooLarge);
        }
        let snap: Snapshot = serde_json::from_str(text).map_err(|_| ReflectError::Parse)?;
        if snap.schema_version != SCHEMA_VERSION {
            return Err(ReflectError::Version);
        }
        let mut store = Self::new(settings, catalog)?;
        let valid = |kind: &str, value: &str| store.catalog.check(kind, value).is_ok();
        let lessons_ok = snap
            .lessons
            .iter()
            .chain(snap.previous.values().flatten())
            .all(|l| valid(&l.kind, &l.value));
        let history_ok = snap
            .history
            .iter()
            .all(|s| s.observed.iter().all(|(k, v)| valid(k, v)));
        let ids_ok = snap.lessons.iter().all(|l| l.id < snap.next_id);
        if !(lessons_ok && history_ok && ids_ok) || snap.history.len() > store.settings.history_cap
        {
            return Err(ReflectError::Invalid);
        }
        store.next_id = snap.next_id;
        store.history = snap.history.into();
        store.lessons = snap.lessons.into_iter().map(|l| (l.id, l)).collect();
        store.previous = snap.previous;
        store.blocked = snap.blocked;
        Ok(store)
    }
}
