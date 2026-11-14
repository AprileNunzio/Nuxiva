use std::collections::{BTreeMap, BTreeSet, VecDeque};

use nuxiva_taskq_core::{SCHEMA_VERSION, TaskSpec};

use crate::clock::{DAY_MS, local};
use crate::error::{ProactivityError, ProactivityResult};
use crate::gate::{Interruptions, PersonPolicy};
use crate::habit::Habit;
use crate::learn::{Feedback, Learner, key};
use crate::model::{Context, Decision, Explanation, Forecast, Signal, Stats, person_ok};
use crate::rules::{Audience, Rule, Ruleset};
use crate::settings::Settings;

#[derive(Debug, Clone)]
pub(crate) enum Origin {
    Signal,
    Habit(u32),
    Forecast(u32),
}

#[derive(Debug, Clone)]
pub(crate) struct Request {
    pub rule: String,
    pub person: Option<String>,
    pub subject: String,
    pub origin: Origin,
}

#[derive(Debug, Clone)]
pub(crate) struct Deferred {
    pub request: Request,
    pub expires_at: u64,
}

#[derive(Debug, Clone)]
pub(crate) struct UndoEntry {
    pub id: u64,
    pub rule: String,
    pub person: Option<String>,
    pub task: TaskSpec,
    pub expires_at: u64,
}

#[derive(Debug, Clone)]
pub(crate) struct Fact {
    pub value: i32,
    pub at: u64,
}

#[derive(Debug)]
pub struct Engine {
    pub(crate) settings: Settings,
    pub(crate) rules: Ruleset,
    pub(crate) facts: BTreeMap<String, Fact>,
    pub(crate) habits: BTreeMap<String, Habit>,
    pub(crate) learner: Learner,
    pub(crate) policies: BTreeMap<String, PersonPolicy>,
    pub(crate) approved: BTreeSet<String>,
    pub(crate) pending: VecDeque<Decision>,
    pub(crate) log: VecDeque<Decision>,
    pub(crate) deferred: VecDeque<Deferred>,
    pub(crate) undo: VecDeque<UndoEntry>,
    pub(crate) cooldown: BTreeMap<String, u64>,
    pub(crate) interruptions: Interruptions,
    pub(crate) next_id: u64,
    pub(crate) stats: Stats,
}

pub(crate) fn fact_key(domain: &str, name: &str, person: Option<&str>) -> String {
    format!("{domain}|{name}|{}", person.unwrap_or(""))
}

pub(crate) fn push_capped<T>(queue: &mut VecDeque<T>, item: T, cap: usize) {
    if queue.len() >= cap {
        queue.pop_front();
    }
    queue.push_back(item);
}

impl Engine {
    pub fn new(settings: Settings, rules: Ruleset) -> ProactivityResult<Self> {
        settings.validate()?;
        rules.validate()?;
        Ok(Self {
            settings,
            rules,
            facts: BTreeMap::new(),
            habits: BTreeMap::new(),
            learner: Learner::default(),
            policies: BTreeMap::new(),
            approved: BTreeSet::new(),
            pending: VecDeque::new(),
            log: VecDeque::new(),
            deferred: VecDeque::new(),
            undo: VecDeque::new(),
            cooldown: BTreeMap::new(),
            interruptions: Interruptions::default(),
            next_id: 1,
            stats: Stats::default(),
        })
    }

    pub(crate) fn note_days(&mut self, ctx: &Context, now: u64) {
        let at = local(now, ctx.tz_offset_min);
        for habit in self.habits.values_mut() {
            habit.note_day(&at);
        }
    }

    pub(crate) fn prune(&mut self, now: u64) {
        let ttl = self.settings.signal_ttl_ms;
        self.facts.retain(|_, f| now.saturating_sub(f.at) <= ttl);
        self.cooldown.retain(|_, until| *until > now);
        self.undo.retain(|u| u.expires_at > now);
    }

    pub fn ingest(
        &mut self,
        signal: &Signal,
        ctx: &Context,
        now: u64,
    ) -> ProactivityResult<Vec<Decision>> {
        if !signal.valid() || !ctx.valid() {
            return Err(ProactivityError::Invalid);
        }
        self.prune(now);
        self.note_days(ctx, now);
        let name = signal.domain.name();
        let at = local(now, ctx.tz_offset_min);
        if self.facts.len() < 4_096
            || self
                .facts
                .contains_key(&fact_key(name, &signal.key, signal.person.as_deref()))
        {
            self.facts.insert(
                fact_key(name, &signal.key, signal.person.as_deref()),
                Fact {
                    value: signal.value,
                    at: signal.at.min(now),
                },
            );
        }
        let matching: Vec<(String, Rule)> = self
            .rules
            .rules
            .iter()
            .filter(|(_, r)| {
                r.trigger.domain == signal.domain
                    && r.trigger.key == signal.key
                    && r.trigger.test(Some(signal.value))
            })
            .map(|(id, r)| (id.clone(), r.clone()))
            .collect();
        let mut out = Vec::new();
        for (id, rule) in matching {
            let person = match rule.audience {
                Audience::Subject => signal.person.clone(),
                Audience::Household => None,
            };
            if rule.audience == Audience::Subject && person.is_none() {
                continue;
            }
            if rule.habit.is_some()
                && (self.habits.len() < 4_096
                    || self.habits.contains_key(&key(&id, person.as_deref())))
            {
                self.habits
                    .entry(key(&id, person.as_deref()))
                    .or_default()
                    .record(&at);
            }
            let request = Request {
                rule: id.clone(),
                person: person.clone(),
                subject: signal.subject.clone(),
                origin: Origin::Signal,
            };
            let cool = format!("s|{}|{}", key(&id, person.as_deref()), signal.subject);
            if self.cooldown.get(&cool).is_some_and(|until| *until > now) {
                continue;
            }
            if let Some(decision) = self.run(&request, ctx, now, None) {
                let hold = rule.cooldown_ms.max(self.settings.dedupe_ms);
                if self.cooldown.len() < 8_192 {
                    self.cooldown.insert(cool, now.saturating_add(hold));
                }
                out.push(decision);
            }
        }
        Ok(out)
    }

    pub fn forecast(
        &mut self,
        forecast: &Forecast,
        ctx: &Context,
        now: u64,
    ) -> ProactivityResult<Vec<Decision>> {
        if !forecast.valid() || !ctx.valid() {
            return Err(ProactivityError::Invalid);
        }
        let rule = self
            .rules
            .rules
            .get(&forecast.rule)
            .ok_or(ProactivityError::NotFound)?;
        if rule.audience == Audience::Subject && forecast.person.is_none() {
            return Err(ProactivityError::Invalid);
        }
        let person = match rule.audience {
            Audience::Subject => forecast.person.clone(),
            Audience::Household => None,
        };
        self.prune(now);
        let cool = format!(
            "f|{}|{}",
            key(&forecast.rule, person.as_deref()),
            forecast.subject
        );
        if self.cooldown.get(&cool).is_some_and(|until| *until > now) {
            return Ok(Vec::new());
        }
        if self.cooldown.len() < 8_192 {
            self.cooldown
                .insert(cool, now.saturating_add(self.settings.dedupe_ms));
        }
        let request = Request {
            rule: forecast.rule.clone(),
            person,
            subject: forecast.subject.clone(),
            origin: Origin::Forecast(forecast.probability),
        };
        Ok(self.run(&request, ctx, now, None).into_iter().collect())
    }

    pub fn tick(&mut self, ctx: &Context, now: u64) -> ProactivityResult<Vec<Decision>> {
        if !ctx.valid() {
            return Err(ProactivityError::Invalid);
        }
        self.prune(now);
        self.note_days(ctx, now);
        self.expire_pending(now);
        let mut out = Vec::new();
        let waiting: Vec<Deferred> = self.deferred.drain(..).collect();
        for item in waiting {
            if item.expires_at <= now {
                continue;
            }
            if let Some(decision) = self.run(&item.request, ctx, now, Some(item.expires_at)) {
                out.push(decision);
            }
        }
        out.extend(self.predict(ctx, now));
        Ok(out)
    }

    fn expire_pending(&mut self, now: u64) {
        let (live, dead): (Vec<Decision>, Vec<Decision>) =
            self.pending.drain(..).partition(|d| d.expires_at > now);
        self.pending = live.into();
        for d in dead {
            self.stats.expired = self.stats.expired.saturating_add(1);
            let k = key(&d.rule, d.person.as_deref());
            self.learner
                .feedback(&k, Feedback::Ignored, now, self.settings.mute_ms);
        }
    }

    fn predict(&mut self, ctx: &Context, now: u64) -> Vec<Decision> {
        let mut due: Vec<Request> = Vec::new();
        for (habit_key, habit) in &self.habits {
            let Some((rule_id, person)) = habit_key.split_once('|') else {
                continue;
            };
            let Some(spec) = self.rules.rules.get(rule_id).and_then(|r| r.habit) else {
                continue;
            };
            let target = local(now.saturating_add(spec.lead_ms), ctx.tz_offset_min);
            let Some(p) = habit.probability(&target, spec.min_days) else {
                continue;
            };
            let person = if person.is_empty() {
                None
            } else {
                Some(person.to_owned())
            };
            if p < spec.min_permille || person.as_deref().is_some_and(|x| !person_ok(x)) {
                continue;
            }
            let cool = format!("h|{habit_key}|{}|{}", target.day, target.minute / 60);
            if self.cooldown.contains_key(&cool) || self.cooldown.len() >= 8_192 {
                continue;
            }
            self.cooldown.insert(cool, now.saturating_add(DAY_MS));
            due.push(Request {
                rule: rule_id.to_owned(),
                person,
                subject: String::new(),
                origin: Origin::Habit(p),
            });
        }
        due.iter()
            .filter_map(|request| self.run(request, ctx, now, None))
            .collect()
    }

    #[must_use]
    pub fn pending(&self) -> Vec<&Decision> {
        self.pending.iter().collect()
    }

    #[must_use]
    pub fn log(&self) -> Vec<&Decision> {
        self.log.iter().collect()
    }

    pub fn explain(&self, id: u64) -> ProactivityResult<&Explanation> {
        self.pending
            .iter()
            .chain(self.log.iter())
            .find(|d| d.id == id)
            .map(|d| &d.explanation)
            .ok_or(ProactivityError::NotFound)
    }

    #[must_use]
    pub fn undoable(&self) -> Vec<u64> {
        self.undo.iter().map(|u| u.id).collect()
    }

    #[must_use]
    pub const fn stats(&self) -> Stats {
        self.stats
    }

    #[must_use]
    pub fn acceptance_permille(&self) -> Option<u32> {
        let decided = self
            .stats
            .accepted
            .saturating_add(self.stats.refused)
            .saturating_add(self.stats.undone);
        let share = self
            .stats
            .accepted
            .saturating_mul(1_000)
            .checked_div(decided)?;
        u32::try_from(share).ok()
    }

    pub(crate) fn build_task(&self, rule_id: &str, rule: &Rule, subject: &str) -> Option<TaskSpec> {
        let spec = TaskSpec {
            schema_version: SCHEMA_VERSION,
            id: format!("pro.{rule_id}.{}", self.next_id),
            parent: None,
            kind: rule.action.kind.clone(),
            class: rule.action.class,
            priority: rule.action.priority,
            deps: Vec::new(),
            scope: rule.action.scope.clone(),
            budget: rule.action.budget,
            risk_max: rule.action.risk_max,
            input_ref: rule.action.input_template.replace("{subject}", subject),
            idem_key: None,
        };
        spec.validate().ok().map(|()| spec)
    }

    pub(crate) fn register_undo(&mut self, decision: &Decision, now: u64) {
        let Some(rule) = self.rules.rules.get(&decision.rule) else {
            return;
        };
        let Some(undo) = rule.action.undo.as_ref() else {
            return;
        };
        let spec = TaskSpec {
            schema_version: SCHEMA_VERSION,
            id: format!("pro.undo.{}.{}", decision.rule, decision.id),
            parent: decision.action.as_ref().map(|a| a.id.clone()),
            kind: undo.kind.clone(),
            class: rule.action.class,
            priority: rule.action.priority,
            deps: Vec::new(),
            scope: rule.action.scope.clone(),
            budget: rule.action.budget,
            risk_max: rule.action.risk_max,
            input_ref: undo.input_template.replace("{subject}", &decision.subject),
            idem_key: None,
        };
        if spec.validate().is_ok() {
            push_capped(
                &mut self.undo,
                UndoEntry {
                    id: decision.id,
                    rule: decision.rule.clone(),
                    person: decision.person.clone(),
                    task: spec,
                    expires_at: now.saturating_add(undo.window_ms),
                },
                64,
            );
        }
    }
}
