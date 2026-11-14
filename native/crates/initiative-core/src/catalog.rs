use std::collections::BTreeMap;

use nuxiva_taskq_core::{Budget, Class, Risk, valid_ident};
use serde::{Deserialize, Serialize};

use crate::error::{InitiativeError, InitiativeResult};
use crate::settings::MAX_PAYLOAD;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Source {
    Bus,
    Fs,
    Presence,
    Vision,
    Calendar,
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

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ActionTemplate {
    pub kind: String,
    pub class: Class,
    pub priority: u8,
    pub budget: Budget,
    pub risk_max: Risk,
    pub input_template: String,
    #[serde(default)]
    pub scope: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Observer {
    pub source: Source,
    pub topic: String,
    #[serde(default)]
    pub subject_prefix: String,
    pub summary_key: String,
    pub value: u32,
    pub confidence: u32,
    pub level: Level,
    pub action: ActionTemplate,
}

#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Catalog {
    pub observers: BTreeMap<String, Observer>,
}

pub fn subject_ok(text: &str) -> bool {
    text.len() <= 240 && !text.chars().any(char::is_control)
}

impl Catalog {
    pub fn validate(&self) -> InitiativeResult<()> {
        let ok = !self.observers.is_empty()
            && self.observers.len() <= 1_024
            && self.observers.iter().all(|(id, o)| {
                valid_ident(id)
                    && valid_ident(&o.topic)
                    && valid_ident(&o.summary_key)
                    && subject_ok(&o.subject_prefix)
                    && o.value <= 1_000
                    && o.confidence <= 1_000
                    && !o.action.kind.is_empty()
                    && o.action.kind.len() <= 32
                    && o.action.input_template.len() <= 400
                    && !o.action.input_template.chars().any(char::is_control)
                    && o.action.scope.iter().all(|s| valid_ident(s))
                    && (1..=86_400_000).contains(&o.action.budget.wall_ms)
                    && !(o.level == Level::DoAndTell && o.action.risk_max > Risk::Low)
            });
        if ok {
            Ok(())
        } else {
            Err(InitiativeError::Catalog)
        }
    }

    pub fn from_json(text: &str) -> InitiativeResult<Self> {
        if text.len() > MAX_PAYLOAD {
            return Err(InitiativeError::TooLarge);
        }
        let catalog: Self = serde_json::from_str(text).map_err(|_| InitiativeError::Catalog)?;
        catalog.validate()?;
        Ok(catalog)
    }
}
