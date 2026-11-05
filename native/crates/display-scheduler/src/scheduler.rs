use crate::cadence::Cadence;
use crate::entry::Entry;
use crate::error::SchedulerError;
use crate::health::Health;
use crate::lifecycle::{Lifecycle, Transition};
use crate::policy::Policy;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

pub const MAX_INSTANCE_ID: usize = 96;

#[derive(Debug, Clone, PartialEq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WidgetInput {
    pub instance: String,
    pub widget: String,
    pub cadence: Cadence,
    #[serde(default)]
    pub cost_mb: f32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Due {
    pub instance: String,
    pub widget: String,
    pub screen: u16,
}

#[derive(Debug, Default)]
pub struct Scheduler {
    policy: Policy,
    widgets: BTreeMap<String, Entry>,
    deadlines: BTreeSet<(u64, String)>,
    sleeping: BTreeMap<u16, u64>,
    health: Health,
}

fn valid_id(raw: &str) -> bool {
    !raw.is_empty()
        && raw.len() <= MAX_INSTANCE_ID
        && raw
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-' | b':' | b'.' | b'@'))
}

impl Scheduler {
    #[must_use]
    pub fn new(policy: Policy) -> Self {
        Self {
            policy,
            ..Self::default()
        }
    }

    #[must_use]
    pub fn state(&self, instance: &str) -> Option<Lifecycle> {
        self.widgets.get(instance).map(|e| e.state)
    }

    #[must_use]
    pub fn screen_cost(&self, screen: u16) -> f32 {
        self.widgets
            .values()
            .filter(|e| e.screen == screen && e.state.holds_gpu())
            .map(|e| e.cost_mb)
            .sum()
    }

    #[must_use]
    pub fn quarantined(&self, now_ms: u64) -> Vec<String> {
        self.health.quarantined(now_ms)
    }

    pub fn admit(
        &mut self,
        screen: u16,
        plan: &[WidgetInput],
        now_ms: u64,
    ) -> Result<Vec<Transition>, SchedulerError> {
        if plan
            .iter()
            .any(|w| !valid_id(&w.instance) || !valid_id(&w.widget))
        {
            return Err(SchedulerError::InstanceId);
        }
        if plan
            .iter()
            .any(|w| !w.cost_mb.is_finite() || w.cost_mb < 0.0)
        {
            return Err(SchedulerError::Cost);
        }
        let wanted: BTreeSet<&str> = plan.iter().map(|w| w.instance.as_str()).collect();
        let mut out = Vec::new();
        let gone: Vec<String> = self
            .widgets
            .iter()
            .filter(|(id, e)| e.screen == screen && !wanted.contains(id.as_str()))
            .map(|(id, _)| id.clone())
            .collect();
        for id in gone {
            self.move_to(&id, Lifecycle::Dormant, "plan.removed", now_ms, &mut out);
            self.forget(&id);
        }
        let room = self.policy.max_widgets.saturating_sub(self.widgets.len());
        let fresh = plan
            .iter()
            .filter(|w| !self.widgets.contains_key(&w.instance))
            .count();
        if fresh > room {
            return Err(SchedulerError::TooManyWidgets);
        }
        let asleep = self.sleeping.contains_key(&screen);
        for w in plan {
            if self.health.blocked(&w.widget, now_ms) || self.widgets.contains_key(&w.instance) {
                continue;
            }
            let state = if asleep {
                Lifecycle::Dormant
            } else {
                Lifecycle::Warm
            };
            let entry = Entry {
                widget: w.widget.clone(),
                screen,
                state,
                cadence: w.cadence,
                cost_mb: w.cost_mb,
                since_ms: now_ms,
                next_due_ms: None,
            };
            self.widgets.insert(w.instance.clone(), entry);
            self.reschedule(&w.instance, now_ms);
            out.push(Transition {
                instance: w.instance.clone(),
                screen,
                from: Lifecycle::Dormant,
                to: state,
                reason: "plan.added",
            });
        }
        Ok(out)
    }

    pub fn visibility(
        &mut self,
        instance: &str,
        visible: bool,
        now_ms: u64,
    ) -> Result<Vec<Transition>, SchedulerError> {
        let entry = self
            .widgets
            .get(instance)
            .ok_or(SchedulerError::UnknownInstance)?;
        if self.sleeping.contains_key(&entry.screen) {
            return Ok(Vec::new());
        }
        let target = match (entry.state, visible) {
            (
                Lifecycle::Warm | Lifecycle::Frozen | Lifecycle::Hibernated | Lifecycle::Dormant,
                true,
            ) => Lifecycle::Live,
            (Lifecycle::Live, false) => Lifecycle::Frozen,
            (state, _) => state,
        };
        let mut out = Vec::new();
        self.move_to(
            instance,
            target,
            if visible {
                "view.visible"
            } else {
                "view.hidden"
            },
            now_ms,
            &mut out,
        );
        Ok(out)
    }

    pub fn observe(&mut self, instance: &str, cost_mb: f32) -> Result<(), SchedulerError> {
        if !cost_mb.is_finite() || cost_mb < 0.0 {
            return Err(SchedulerError::Cost);
        }
        let k = self.policy.cost_smoothing.clamp(0.01, 1.0);
        let entry = self
            .widgets
            .get_mut(instance)
            .ok_or(SchedulerError::UnknownInstance)?;
        entry.cost_mb = entry.cost_mb.mul_add(1.0 - k, cost_mb * k);
        Ok(())
    }

    pub fn error(
        &mut self,
        instance: &str,
        now_ms: u64,
    ) -> Result<Vec<Transition>, SchedulerError> {
        let widget = self
            .widgets
            .get(instance)
            .ok_or(SchedulerError::UnknownInstance)?
            .widget
            .clone();
        let p = self.policy;
        let mut out = Vec::new();
        if self.health.record(
            &widget,
            now_ms,
            p.error_window_ms,
            p.error_limit,
            p.quarantine_ms,
        ) {
            let hit: Vec<String> = self
                .widgets
                .iter()
                .filter(|(_, e)| e.widget == widget)
                .map(|(id, _)| id.clone())
                .collect();
            for id in hit {
                self.move_to(
                    &id,
                    Lifecycle::Dormant,
                    "health.quarantine",
                    now_ms,
                    &mut out,
                );
                self.forget(&id);
            }
        }
        Ok(out)
    }

    pub fn pressure(&mut self, screen: u16, budget_mb: f32, now_ms: u64) -> Vec<Transition> {
        let mut out = Vec::new();
        let mut frozen: Vec<(String, f32)> = self
            .widgets
            .iter()
            .filter(|(_, e)| e.screen == screen && e.state == Lifecycle::Frozen)
            .map(|(id, e)| (id.clone(), e.cost_mb))
            .collect();
        frozen.sort_by(|a, b| b.1.total_cmp(&a.1));
        for (id, _) in frozen {
            if self.screen_cost(screen) <= budget_mb {
                break;
            }
            self.move_to(
                &id,
                Lifecycle::Hibernated,
                "budget.pressure",
                now_ms,
                &mut out,
            );
        }
        out
    }

    pub fn audience(&mut self, screen: u16, nucleus_only: bool, now_ms: u64) -> Vec<Transition> {
        let mut out = Vec::new();
        if !nucleus_only {
            if self.sleeping.remove(&screen).is_some() {
                let ids = self.on_screen(screen);
                for id in ids {
                    if self
                        .widgets
                        .get(&id)
                        .is_some_and(|e| e.state == Lifecycle::Dormant)
                    {
                        self.move_to(&id, Lifecycle::Warm, "audience.back", now_ms, &mut out);
                    }
                }
            }
            return out;
        }
        self.sleeping.entry(screen).or_insert(now_ms);
        for id in self.on_screen(screen) {
            if self
                .widgets
                .get(&id)
                .is_some_and(|e| e.state == Lifecycle::Live)
            {
                self.move_to(&id, Lifecycle::Frozen, "audience.away", now_ms, &mut out);
            }
        }
        out
    }

    pub fn tick(&mut self, now_ms: u64) -> (Vec<Due>, Vec<Transition>) {
        self.health.expire(now_ms);
        let mut out = Vec::new();
        let p = self.policy;
        let sleepers: Vec<u16> = self
            .sleeping
            .iter()
            .filter(|(_, since)| now_ms.saturating_sub(**since) >= p.sleep_grace_ms)
            .map(|(s, _)| *s)
            .collect();
        for screen in sleepers {
            for id in self.on_screen(screen) {
                if self
                    .widgets
                    .get(&id)
                    .is_some_and(|e| e.state != Lifecycle::Dormant)
                {
                    self.move_to(&id, Lifecycle::Dormant, "audience.sleep", now_ms, &mut out);
                }
            }
        }
        let stale: Vec<String> = self
            .widgets
            .iter()
            .filter(|(_, e)| {
                e.state == Lifecycle::Frozen
                    && now_ms.saturating_sub(e.since_ms) >= p.hibernate_after_ms
            })
            .map(|(id, _)| id.clone())
            .collect();
        for id in stale {
            self.move_to(
                &id,
                Lifecycle::Hibernated,
                "idle.hibernate",
                now_ms,
                &mut out,
            );
        }
        (self.collect_due(now_ms), out)
    }

    fn collect_due(&mut self, now_ms: u64) -> Vec<Due> {
        let ready: Vec<(u64, String)> = self
            .deadlines
            .iter()
            .take_while(|(t, _)| *t <= now_ms)
            .cloned()
            .collect();
        let mut due = Vec::with_capacity(ready.len());
        for (t, id) in ready {
            self.deadlines.remove(&(t, id.clone()));
            if let Some(e) = self.widgets.get(&id) {
                due.push(Due {
                    instance: id.clone(),
                    widget: e.widget.clone(),
                    screen: e.screen,
                });
            }
            self.reschedule(&id, now_ms);
        }
        due
    }

    fn on_screen(&self, screen: u16) -> Vec<String> {
        self.widgets
            .iter()
            .filter(|(_, e)| e.screen == screen)
            .map(|(id, _)| id.clone())
            .collect()
    }

    fn move_to(
        &mut self,
        id: &str,
        to: Lifecycle,
        reason: &'static str,
        now_ms: u64,
        out: &mut Vec<Transition>,
    ) {
        let Some(entry) = self.widgets.get_mut(id) else {
            return;
        };
        if entry.state == to {
            return;
        }
        out.push(Transition {
            instance: id.to_owned(),
            screen: entry.screen,
            from: entry.state,
            to,
            reason,
        });
        entry.state = to;
        entry.since_ms = now_ms;
        self.reschedule(id, now_ms);
    }

    fn reschedule(&mut self, id: &str, now_ms: u64) {
        let Some(entry) = self.widgets.get_mut(id) else {
            return;
        };
        if let Some(old) = entry.next_due_ms.take() {
            self.deadlines.remove(&(old, id.to_owned()));
        }
        entry.next_due_ms = entry.schedule(now_ms);
        if let Some(t) = entry.next_due_ms {
            self.deadlines.insert((t, id.to_owned()));
        }
    }

    fn forget(&mut self, id: &str) {
        if let Some(entry) = self.widgets.remove(id)
            && let Some(t) = entry.next_due_ms
        {
            self.deadlines.remove(&(t, id.to_owned()));
        }
    }
}
