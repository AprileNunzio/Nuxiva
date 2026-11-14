use std::collections::{BTreeMap, BTreeSet, VecDeque};

use nuxiva_taskq_core::{Risk, SCHEMA_VERSION, TaskSpec, valid_ident};
use serde::{Deserialize, Serialize};

use crate::catalog::{Catalog, Level, Observer, Source, subject_ok};
use crate::error::{InitiativeError, InitiativeResult};
use crate::settings::{MAX_PAYLOAD, Settings, Situation};

const HOUR_MS: u64 = 3_600_000;

#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Event {
    pub source: Source,
    pub topic: String,
    pub subject: String,
    pub at: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Context {
    pub situation: Situation,
    pub voice_free: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Mode {
    Diary,
    Widget,
    Speak,
    Execute,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Proposal {
    pub id: u64,
    pub observer: String,
    pub summary_key: String,
    pub subject: String,
    pub action: TaskSpec,
    pub mode: Mode,
    pub score: i64,
    pub requires_consent: bool,
    pub expires_at: u64,
    pub deferred: bool,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize)]
pub struct Stats {
    pub surfaced: u64,
    pub accepted: u64,
    pub refused: u64,
    pub silent: u64,
    pub capped: u64,
    pub expired: u64,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct State {
    approved: BTreeSet<String>,
    refusals: BTreeMap<String, Vec<u64>>,
}

#[derive(Debug)]
pub struct Engine {
    settings: Settings,
    catalog: Catalog,
    approved: BTreeSet<String>,
    refusals: BTreeMap<String, Vec<u64>>,
    pending: VecDeque<Proposal>,
    diary: VecDeque<Proposal>,
    seen: VecDeque<(String, u64)>,
    window: VecDeque<u64>,
    next_id: u64,
    stats: Stats,
}

impl Engine {
    pub fn new(settings: Settings, catalog: Catalog) -> InitiativeResult<Self> {
        settings.validate()?;
        catalog.validate()?;
        Ok(Self {
            settings,
            catalog,
            approved: BTreeSet::new(),
            refusals: BTreeMap::new(),
            pending: VecDeque::new(),
            diary: VecDeque::new(),
            seen: VecDeque::new(),
            window: VecDeque::new(),
            next_id: 1,
            stats: Stats::default(),
        })
    }

    fn level_of(&self, id: &str, observer: &Observer, now: u64) -> Level {
        let steps = self
            .refusals
            .get(id)
            .map_or(0, |v| v.iter().filter(|until| **until > now).count());
        let mut level = observer.level;
        for _ in 0..steps {
            level = level.lower();
        }
        if level == Level::DoAndTell
            && !(self.approved.contains(id) && observer.action.risk_max <= Risk::Low)
        {
            level = Level::Propose;
        }
        level
    }

    fn build(&mut self, id: &str, observer: &Observer, subject: &str) -> Option<TaskSpec> {
        let spec = TaskSpec {
            schema_version: SCHEMA_VERSION,
            id: format!("init.{id}.{}", self.next_id),
            parent: None,
            kind: observer.action.kind.clone(),
            class: observer.action.class,
            priority: observer.action.priority,
            deps: Vec::new(),
            scope: observer.action.scope.clone(),
            budget: observer.action.budget,
            risk_max: observer.action.risk_max,
            input_ref: observer.action.input_template.replace("{subject}", subject),
            idem_key: None,
        };
        spec.validate().ok().map(|()| spec)
    }

    fn surfaced_recently(&mut self, now: u64) -> usize {
        while self
            .window
            .front()
            .is_some_and(|t| now.saturating_sub(*t) >= HOUR_MS)
        {
            self.window.pop_front();
        }
        self.window.len()
    }

    fn decide(
        &mut self,
        id: &str,
        observer: &Observer,
        subject: &str,
        ctx: Context,
        now: u64,
        deferred_ok: bool,
    ) -> Option<Proposal> {
        let level = self.level_of(id, observer, now);
        let gross = i64::from(observer.value)
            .saturating_mul(i64::from(observer.confidence))
            .checked_div(1_000)
            .unwrap_or(0);
        let score = gross.saturating_sub(i64::from(self.settings.cost(ctx.situation)));
        let action = self.build(id, observer, subject)?;
        let blocked_by_cost = score <= 0;
        let capped = !blocked_by_cost
            && level != Level::Silent
            && self.surfaced_recently(now) >= self.settings.hourly_cap;
        let mode = if level == Level::Silent || blocked_by_cost || capped {
            Mode::Diary
        } else {
            match level {
                Level::DoAndTell => Mode::Execute,
                _ if ctx.voice_free && ctx.situation == Situation::Idle => Mode::Speak,
                _ => Mode::Widget,
            }
        };
        let proposal = Proposal {
            id: self.next_id,
            observer: id.to_owned(),
            summary_key: observer.summary_key.clone(),
            subject: subject.to_owned(),
            action,
            mode,
            score,
            requires_consent: mode != Mode::Execute && observer.action.risk_max >= Risk::Medium,
            expires_at: now.saturating_add(self.settings.proposal_ttl_ms),
            deferred: mode == Mode::Diary
                && level != Level::Silent
                && deferred_ok
                && (blocked_by_cost || capped),
        };
        self.next_id = self.next_id.saturating_add(1);
        if capped {
            self.stats.capped = self.stats.capped.saturating_add(1);
        }
        match mode {
            Mode::Diary => {
                self.stats.silent = self.stats.silent.saturating_add(1);
                Self::push_capped(&mut self.diary, proposal.clone(), self.settings.diary_cap);
            }
            Mode::Execute => {
                self.window.push_back(now);
                self.stats.surfaced = self.stats.surfaced.saturating_add(1);
                Self::push_capped(&mut self.diary, proposal.clone(), self.settings.diary_cap);
            }
            Mode::Widget | Mode::Speak => {
                self.window.push_back(now);
                self.stats.surfaced = self.stats.surfaced.saturating_add(1);
                Self::push_capped(
                    &mut self.pending,
                    proposal.clone(),
                    self.settings.pending_cap,
                );
            }
        }
        Some(proposal)
    }

    fn push_capped(queue: &mut VecDeque<Proposal>, item: Proposal, cap: usize) {
        if queue.len() >= cap {
            queue.pop_front();
        }
        queue.push_back(item);
    }

    pub fn observe(
        &mut self,
        event: &Event,
        ctx: Context,
        now: u64,
    ) -> InitiativeResult<Vec<Proposal>> {
        if !valid_ident(&event.topic) || !subject_ok(&event.subject) {
            return Err(InitiativeError::Invalid);
        }
        while self
            .seen
            .front()
            .is_some_and(|(_, t)| now.saturating_sub(*t) > self.settings.dedupe_ms)
        {
            self.seen.pop_front();
        }
        let matching: Vec<(String, Observer)> = self
            .catalog
            .observers
            .iter()
            .filter(|(_, o)| {
                o.source == event.source
                    && o.topic == event.topic
                    && event.subject.starts_with(&o.subject_prefix)
            })
            .map(|(id, o)| (id.clone(), o.clone()))
            .collect();
        let mut out = Vec::new();
        for (id, observer) in matching {
            let key = format!("{id}|{}", event.subject);
            if self.seen.iter().any(|(k, _)| *k == key) {
                continue;
            }
            self.seen.push_back((key, now));
            if let Some(p) = self.decide(&id, &observer, &event.subject, ctx, now, true) {
                out.push(p);
            }
        }
        Ok(out)
    }

    pub fn tick(&mut self, ctx: Context, now: u64) -> Vec<Proposal> {
        let before = self.pending.len();
        self.pending.retain(|p| p.expires_at > now);
        self.stats.expired = self
            .stats
            .expired
            .saturating_add(u64::try_from(before.saturating_sub(self.pending.len())).unwrap_or(0));
        let ready: Vec<Proposal> = self
            .diary
            .iter()
            .filter(|p| p.deferred && p.expires_at > now)
            .cloned()
            .collect();
        self.diary.retain(|p| {
            !(p.deferred && p.expires_at > now)
                && p.expires_at.saturating_add(self.settings.dedupe_ms) > now
        });
        let mut out = Vec::new();
        for old in ready {
            let Some(observer) = self.catalog.observers.get(&old.observer).cloned() else {
                continue;
            };
            if let Some(p) = self.decide(&old.observer, &observer, &old.subject, ctx, now, true) {
                if p.mode == Mode::Diary {
                    self.stats.silent = self.stats.silent.saturating_sub(1);
                    continue;
                }
                out.push(p);
            }
        }
        out
    }

    pub fn accept(&mut self, id: u64, now: u64) -> InitiativeResult<TaskSpec> {
        let at = self
            .pending
            .iter()
            .position(|p| p.id == id)
            .ok_or(InitiativeError::NotFound)?;
        let proposal = self.pending.remove(at).ok_or(InitiativeError::NotFound)?;
        if proposal.expires_at <= now {
            self.stats.expired = self.stats.expired.saturating_add(1);
            return Err(InitiativeError::State);
        }
        self.stats.accepted = self.stats.accepted.saturating_add(1);
        Ok(proposal.action)
    }

    pub fn refuse(&mut self, id: u64, now: u64) -> InitiativeResult<()> {
        let at = self
            .pending
            .iter()
            .position(|p| p.id == id)
            .ok_or(InitiativeError::NotFound)?;
        let proposal = self.pending.remove(at).ok_or(InitiativeError::NotFound)?;
        let list = self.refusals.entry(proposal.observer).or_default();
        list.retain(|until| *until > now);
        list.push(now.saturating_add(self.settings.refusal_ms));
        self.stats.refused = self.stats.refused.saturating_add(1);
        Ok(())
    }

    pub fn approve_always(&mut self, observer: &str) -> InitiativeResult<()> {
        let found = self
            .catalog
            .observers
            .get(observer)
            .ok_or(InitiativeError::NotFound)?;
        if found.action.risk_max > Risk::Low {
            return Err(InitiativeError::Consent);
        }
        self.approved.insert(observer.to_owned());
        Ok(())
    }

    pub fn revoke(&mut self, observer: &str) {
        self.approved.remove(observer);
    }

    #[must_use]
    pub fn pending(&self) -> Vec<&Proposal> {
        self.pending.iter().collect()
    }

    #[must_use]
    pub fn diary(&self) -> Vec<&Proposal> {
        self.diary.iter().collect()
    }

    #[must_use]
    pub const fn stats(&self) -> Stats {
        self.stats
    }

    #[must_use]
    pub fn acceptance_permille(&self) -> Option<u32> {
        let decided = self.stats.accepted.saturating_add(self.stats.refused);
        let share = self
            .stats
            .accepted
            .saturating_mul(1_000)
            .checked_div(decided)?;
        u32::try_from(share).ok()
    }

    pub fn export_state(&self) -> InitiativeResult<String> {
        serde_json::to_string(&State {
            approved: self.approved.clone(),
            refusals: self.refusals.clone(),
        })
        .map_err(|_| InitiativeError::Serialize)
    }

    pub fn import_state(&mut self, text: &str) -> InitiativeResult<()> {
        if text.len() > MAX_PAYLOAD {
            return Err(InitiativeError::TooLarge);
        }
        let state: State = serde_json::from_str(text).map_err(|_| InitiativeError::Parse)?;
        let known = |id: &String| self.catalog.observers.contains_key(id);
        let safe = state.approved.iter().all(|id| {
            self.catalog
                .observers
                .get(id)
                .is_some_and(|o| o.action.risk_max <= Risk::Low)
        });
        if !safe
            || !state.refusals.keys().all(known)
            || state.refusals.values().any(|v| v.len() > 64)
        {
            return Err(InitiativeError::Invalid);
        }
        self.approved = state.approved;
        self.refusals = state.refusals;
        Ok(())
    }

    pub fn event_from_json(text: &str) -> InitiativeResult<Event> {
        if text.len() > 8 * 1024 {
            return Err(InitiativeError::TooLarge);
        }
        serde_json::from_str(text).map_err(|_| InitiativeError::Parse)
    }
}
