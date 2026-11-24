use std::collections::BTreeSet;

use capability_registry::{Effect, ValueType};
use serde::{Deserialize, Serialize};

use crate::error::{UnderstandError, UnderstandResult};

pub const MAX_RAW_BYTES: usize = 16 * 1024;
pub const MAX_ENTITIES: usize = 24;
pub const MAX_VALUE_BYTES: usize = 512;
pub const MAX_CONSTRAINTS: usize = 12;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Risk {
    Low,
    Medium,
    High,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Source {
    User,
    Memory,
    External,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Entity {
    pub role: String,
    pub ty: ValueType,
    pub value: String,
    pub source: Source,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RawGoal {
    pub intent: String,
    pub language: String,
    pub effects: BTreeSet<Effect>,
    pub entities: Vec<Entity>,
    #[serde(default)]
    pub constraints: Vec<String>,
    pub confidence_bps: u16,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Goal {
    pub intent: String,
    pub language: String,
    pub effects: BTreeSet<Effect>,
    pub entities: Vec<Entity>,
    pub constraints: Vec<String>,
    pub risk: Risk,
    pub confidence_bps: u16,
}

const SENSITIVE_ROLES: [&str; 5] = ["recipient", "account", "address", "payee", "destination"];

fn slug(text: &str, max: usize) -> bool {
    !text.is_empty()
        && text.len() <= max
        && text
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_')
}

fn clean(text: &str) -> bool {
    !text.chars().any(|c| c.is_control() && c != '\n')
}

#[must_use]
pub fn risk_of(effects: &BTreeSet<Effect>) -> Risk {
    if effects.contains(&Effect::Spend) {
        Risk::High
    } else if effects.contains(&Effect::SendExternal) || effects.contains(&Effect::Physical) {
        Risk::Medium
    } else {
        Risk::Low
    }
}

pub fn parse(raw: &str, user_text: &str) -> UnderstandResult<Goal> {
    if raw.len() > MAX_RAW_BYTES {
        return Err(UnderstandError::Invalid("too_large"));
    }
    let goal: RawGoal =
        serde_json::from_str(raw).map_err(|_| UnderstandError::Invalid("schema"))?;
    if !slug(&goal.intent, 64) {
        return Err(UnderstandError::Invalid("intent"));
    }
    let lang_ok = (2..=3).contains(&goal.language.len())
        && goal.language.bytes().all(|b| b.is_ascii_lowercase());
    if !lang_ok {
        return Err(UnderstandError::Invalid("language"));
    }
    if goal.effects.is_empty() || goal.confidence_bps > 10_000 {
        return Err(UnderstandError::Invalid("effects"));
    }
    if goal.entities.len() > MAX_ENTITIES || goal.constraints.len() > MAX_CONSTRAINTS {
        return Err(UnderstandError::Invalid("too_many"));
    }
    if goal
        .constraints
        .iter()
        .any(|c| c.len() > MAX_VALUE_BYTES || !clean(c))
    {
        return Err(UnderstandError::Invalid("constraint"));
    }
    let acts_outward =
        goal.effects.contains(&Effect::SendExternal) || goal.effects.contains(&Effect::Spend);
    for entity in &goal.entities {
        if !slug(&entity.role, 32) || entity.value.len() > MAX_VALUE_BYTES || !clean(&entity.value)
        {
            return Err(UnderstandError::Invalid("entity"));
        }
        if entity.source == Source::User && !user_text.contains(entity.value.as_str()) {
            return Err(UnderstandError::Rejected("not_verbatim"));
        }
        if acts_outward
            && entity.source == Source::External
            && SENSITIVE_ROLES.contains(&entity.role.as_str())
        {
            return Err(UnderstandError::Rejected("external_target"));
        }
    }
    let risk = risk_of(&goal.effects);
    Ok(Goal {
        intent: goal.intent,
        language: goal.language,
        effects: goal.effects,
        entities: goal.entities,
        constraints: goal.constraints,
        risk,
        confidence_bps: goal.confidence_bps,
    })
}
