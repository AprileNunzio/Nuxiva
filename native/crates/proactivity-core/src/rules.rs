use std::collections::BTreeMap;

use nuxiva_taskq_core::{Budget, Class, Risk, valid_ident};
use serde::{Deserialize, Serialize};

use crate::clock::{Local, in_span};
use crate::error::{ProactivityError, ProactivityResult};
use crate::model::{Domain, Level, Privacy, Urgency, text_ok};
use crate::settings::MAX_PAYLOAD;

const FORBIDDEN_KIND_PREFIXES: [&str; 9] = [
    "door", "lock", "unlock", "payment", "pay", "delete", "erase", "wipe", "transfer",
];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Cmp {
    Ge,
    Le,
    Eq,
    Present,
    Absent,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Condition {
    pub domain: Domain,
    pub key: String,
    pub cmp: Cmp,
    #[serde(default)]
    pub threshold: i32,
    #[serde(default)]
    pub same_person: bool,
}

impl Condition {
    #[must_use]
    pub fn test(&self, value: Option<i32>) -> bool {
        match (self.cmp, value) {
            (Cmp::Present, v) => v.is_some(),
            (Cmp::Absent, v) => v.is_none(),
            (Cmp::Ge, Some(v)) => v >= self.threshold,
            (Cmp::Le, Some(v)) => v <= self.threshold,
            (Cmp::Eq, Some(v)) => v == self.threshold,
            _ => false,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Window {
    pub start_min: u32,
    pub end_min: u32,
    #[serde(default = "all_days")]
    pub weekdays: u8,
}

const fn all_days() -> u8 {
    0b111_1111
}

impl Window {
    #[must_use]
    pub fn contains(&self, at: &Local) -> bool {
        let day_ok = u32::try_from(at.weekday)
            .ok()
            .and_then(|d| 1_u8.checked_shl(d))
            .is_some_and(|bit| self.weekdays & bit != 0);
        day_ok && in_span(at.minute, self.start_min, self.end_min)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HabitSpec {
    pub lead_ms: u64,
    pub min_days: u32,
    pub min_permille: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Undo {
    pub kind: String,
    pub input_template: String,
    pub window_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ActionSpec {
    pub kind: String,
    pub class: Class,
    pub priority: u8,
    pub budget: Budget,
    pub risk_max: Risk,
    pub input_template: String,
    #[serde(default)]
    pub scope: Vec<String>,
    #[serde(default)]
    pub undo: Option<Undo>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Audience {
    Subject,
    Household,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Rule {
    pub domain: Domain,
    pub trigger: Condition,
    #[serde(default)]
    pub when: Vec<Condition>,
    #[serde(default)]
    pub window: Option<Window>,
    pub audience: Audience,
    pub privacy: Privacy,
    pub urgency: Urgency,
    pub level: Level,
    pub base_confidence: u32,
    pub min_confidence: u32,
    pub value: u32,
    #[serde(default)]
    pub cooldown_ms: u64,
    pub summary_key: String,
    #[serde(default)]
    pub habit: Option<HabitSpec>,
    pub action: ActionSpec,
}

fn forbidden(kind: &str) -> bool {
    FORBIDDEN_KIND_PREFIXES.iter().any(|p| kind.starts_with(*p))
}

fn kind_ok(kind: &str) -> bool {
    !kind.is_empty()
        && kind.len() <= 32
        && kind.bytes().all(|b| {
            b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'.' | b'_' | b'-')
        })
        && !forbidden(kind)
}

fn template_ok(text: &str) -> bool {
    text.len() <= 400 && !text.chars().any(char::is_control)
}

fn condition_ok(c: &Condition) -> bool {
    valid_ident(&c.key) && (-1_000_000..=1_000_000).contains(&c.threshold)
}

impl Rule {
    fn valid(&self) -> bool {
        let action = &self.action;
        let undo_ok = action.undo.as_ref().is_none_or(|u| {
            kind_ok(&u.kind)
                && template_ok(&u.input_template)
                && (1..=7 * 86_400_000).contains(&u.window_ms)
        });
        let habit_ok = self.habit.is_none_or(|h| {
            h.lead_ms <= 6 * 3_600_000 && (1..=365).contains(&h.min_days) && h.min_permille <= 1_000
        });
        let window_ok = self.window.is_none_or(|w| {
            w.start_min < 1_440 && w.end_min < 1_440 && w.weekdays != 0 && w.weekdays < 128
        });
        let execute_ok = self.level != Level::DoAndTell
            || (action.risk_max <= Risk::Low
                && action.undo.is_some()
                && self.urgency == Urgency::Normal);
        condition_ok(&self.trigger)
            && self.trigger.cmp != Cmp::Absent
            && self.when.len() <= 8
            && self.when.iter().all(condition_ok)
            && valid_ident(&self.summary_key)
            && self.base_confidence <= 1_000
            && self.min_confidence <= 1_000
            && self.value <= 1_000
            && self.cooldown_ms <= 7 * 86_400_000
            && kind_ok(&action.kind)
            && template_ok(&action.input_template)
            && action.scope.iter().all(|s| valid_ident(s))
            && (1..=86_400_000).contains(&action.budget.wall_ms)
            && undo_ok
            && habit_ok
            && window_ok
            && execute_ok
            && text_ok(&self.summary_key)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Ruleset {
    pub rules: BTreeMap<String, Rule>,
}

impl Ruleset {
    pub fn validate(&self) -> ProactivityResult<()> {
        let ok = !self.rules.is_empty()
            && self.rules.len() <= 1_024
            && self
                .rules
                .iter()
                .all(|(id, rule)| valid_ident(id) && !id.contains('|') && rule.valid());
        if ok {
            Ok(())
        } else {
            Err(ProactivityError::Rules)
        }
    }

    pub fn from_json(text: &str) -> ProactivityResult<Self> {
        if text.len() > MAX_PAYLOAD {
            return Err(ProactivityError::TooLarge);
        }
        let rules: Self = serde_json::from_str(text).map_err(|_| ProactivityError::Rules)?;
        rules.validate()?;
        Ok(rules)
    }
}
