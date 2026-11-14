use std::collections::BTreeMap;

use nuxiva_taskq_core::{TaskSpec, valid_ident};
use serde::{Deserialize, Serialize};

use crate::clock::MAX_OFFSET_MIN;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Domain {
    Presence,
    Schedule,
    Calendar,
    Health,
    Home,
    Email,
    Security,
}

impl Domain {
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Presence => "presence",
            Self::Schedule => "schedule",
            Self::Calendar => "calendar",
            Self::Health => "health",
            Self::Home => "home",
            Self::Email => "email",
            Self::Security => "security",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Situation {
    Idle,
    Conversation,
    Sleeping,
    Guests,
    Meeting,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Urgency {
    Normal,
    Critical,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Privacy {
    Public,
    Household,
    Private,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Level {
    Silent,
    Notify,
    Propose,
    DoAndTell,
}

impl Level {
    #[must_use]
    pub const fn lower(self) -> Self {
        match self {
            Self::DoAndTell => Self::Propose,
            Self::Propose => Self::Notify,
            Self::Notify | Self::Silent => Self::Silent,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Mode {
    Diary,
    Widget,
    Speak,
    Execute,
}

pub fn text_ok(text: &str) -> bool {
    text.len() <= 240 && !text.chars().any(char::is_control)
}

pub fn person_ok(text: &str) -> bool {
    valid_ident(text) && !text.contains('|')
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Signal {
    pub domain: Domain,
    pub key: String,
    #[serde(default)]
    pub person: Option<String>,
    #[serde(default)]
    pub subject: String,
    #[serde(default)]
    pub value: i32,
    pub at: u64,
}

impl Signal {
    #[must_use]
    pub fn valid(&self) -> bool {
        valid_ident(&self.key)
            && text_ok(&self.subject)
            && (-1_000_000..=1_000_000).contains(&self.value)
            && self.person.as_deref().is_none_or(person_ok)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Context {
    pub situation: Situation,
    #[serde(default)]
    pub voice_free: bool,
    #[serde(default)]
    pub guests_present: bool,
    #[serde(default)]
    pub present: Vec<String>,
    #[serde(default)]
    pub tz_offset_min: i32,
}

impl Context {
    #[must_use]
    pub fn valid(&self) -> bool {
        self.present.len() <= 32
            && self.present.iter().all(|p| person_ok(p))
            && (-MAX_OFFSET_MIN..=MAX_OFFSET_MIN).contains(&self.tz_offset_min)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Forecast {
    pub rule: String,
    #[serde(default)]
    pub person: Option<String>,
    #[serde(default)]
    pub subject: String,
    pub probability: u32,
}

impl Forecast {
    #[must_use]
    pub fn valid(&self) -> bool {
        valid_ident(&self.rule)
            && text_ok(&self.subject)
            && self.probability <= 1_000
            && self.person.as_deref().is_none_or(person_ok)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Reason {
    pub code: &'static str,
    pub params: BTreeMap<&'static str, String>,
}

impl Reason {
    #[must_use]
    pub fn new(code: &'static str) -> Self {
        Self {
            code,
            params: BTreeMap::new(),
        }
    }

    #[must_use]
    #[allow(clippy::needless_pass_by_value)]
    pub fn with(mut self, key: &'static str, value: impl ToString) -> Self {
        self.params.insert(key, value.to_string());
        self
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Explanation {
    pub rule: String,
    pub origin: &'static str,
    pub confidence: u32,
    pub threshold: u32,
    pub score: i64,
    pub reasons: Vec<Reason>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[allow(clippy::struct_excessive_bools)]
pub struct Decision {
    pub id: u64,
    pub rule: String,
    pub person: Option<String>,
    pub summary_key: String,
    pub subject: String,
    pub action: Option<TaskSpec>,
    pub mode: Mode,
    pub confidence: u32,
    pub score: i64,
    pub requires_consent: bool,
    pub redacted: bool,
    pub deferred: bool,
    pub undoable: bool,
    pub created_at: u64,
    pub expires_at: u64,
    pub explanation: Explanation,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize)]
pub struct Stats {
    pub surfaced: u64,
    pub accepted: u64,
    pub refused: u64,
    pub undone: u64,
    pub silent: u64,
    pub capped: u64,
    pub blocked: u64,
    pub expired: u64,
}
