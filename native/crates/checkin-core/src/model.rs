use serde::{Deserialize, Serialize};

use crate::error::{CheckinError, CheckinResult};

pub const MAX_FACTS: usize = 64;
pub const MAX_TURNS: usize = 64;
pub const MAX_FIELD: usize = 200;
pub const MAX_TERMS: usize = 16;
pub const MAX_FOCUS: usize = 8;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Kind {
    Alert,
    Notice,
    Agenda,
    Interest,
    Info,
    Ok,
}

impl Kind {
    #[must_use]
    pub fn half_life(self) -> f64 {
        match self {
            Self::Alert => 1_800.0,
            Self::Notice => 4.0 * 3_600.0,
            Self::Agenda => 3.0 * 3_600.0,
            Self::Interest => 6.0 * 3_600.0,
            Self::Info => 12.0 * 3_600.0,
            Self::Ok => 2.0 * 3_600.0,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct Fact {
    pub key: String,
    pub topic: String,
    pub kind: Kind,
    pub priority: u8,
    pub signature: String,
    pub observed_at: i64,
    pub ttl: i64,
    #[serde(default)]
    pub starts_at: Option<i64>,
    #[serde(default)]
    pub terms: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct Turn {
    pub at: i64,
    #[serde(default)]
    pub told: Vec<String>,
    #[serde(default)]
    pub style: String,
    #[serde(default)]
    pub humor: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
pub struct Moment {
    pub now: i64,
    pub hour: u8,
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct Request {
    pub moment: Moment,
    #[serde(default)]
    pub facts: Vec<Fact>,
    #[serde(default)]
    pub history: Vec<Turn>,
    #[serde(default)]
    pub focus: Vec<String>,
    #[serde(default)]
    pub voice: bool,
    #[serde(default)]
    pub seed: u64,
}

fn bounded(value: &str, what: &'static str) -> CheckinResult<()> {
    if value.len() > MAX_FIELD {
        return Err(CheckinError::TooLarge(what));
    }
    if value.chars().any(char::is_control) {
        return Err(CheckinError::Invalid(format!(
            "{what} contains control characters"
        )));
    }
    Ok(())
}

impl Request {
    pub fn validate(&self) -> CheckinResult<()> {
        if self.facts.len() > MAX_FACTS {
            return Err(CheckinError::TooLarge("facts"));
        }
        if self.history.len() > MAX_TURNS {
            return Err(CheckinError::TooLarge("history"));
        }
        if self.focus.len() > MAX_FOCUS {
            return Err(CheckinError::TooLarge("focus"));
        }
        if self.moment.hour > 23 {
            return Err(CheckinError::Invalid("hour".to_owned()));
        }
        for f in &self.facts {
            bounded(&f.key, "key")?;
            bounded(&f.topic, "topic")?;
            bounded(&f.signature, "signature")?;
            if f.priority > 100 {
                return Err(CheckinError::Invalid("priority".to_owned()));
            }
            if f.terms.len() > MAX_TERMS {
                return Err(CheckinError::TooLarge("terms"));
            }
            f.terms.iter().try_for_each(|t| bounded(t, "term"))?;
        }
        for t in &self.history {
            if t.told.len() > MAX_FACTS {
                return Err(CheckinError::TooLarge("told"));
            }
            bounded(&t.style, "style")?;
            t.told.iter().try_for_each(|s| bounded(s, "told"))?;
        }
        self.focus.iter().try_for_each(|f| bounded(f, "focus"))
    }
}
