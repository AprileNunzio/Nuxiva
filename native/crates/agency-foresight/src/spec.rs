use std::collections::BTreeSet;

use serde::{Deserialize, Serialize};

use crate::error::ForesightError;

pub const MAX_AGENTS: usize = 2_000;
pub const MAX_ENTITIES: usize = 1_000;
pub const MAX_RELATIONS: usize = 8_000;
pub const MAX_EVENTS: usize = 256;
pub const MAX_ROUNDS: u16 = 720;
pub const MAX_FOLLOWS: usize = 256;
const MAX_KEY: usize = 64;
const MAX_NAME: usize = 120;
const MAX_LABEL: usize = 60;
const MAX_TEXT: usize = 2_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Platform {
    Feed,
    Forum,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EntitySpec {
    pub key: String,
    pub name: String,
    pub kind: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RelationSpec {
    pub from: String,
    pub to: String,
    pub kind: String,
    pub weight: f64,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Traits {
    pub stance: f64,
    pub openness: f64,
    pub activity: f64,
    pub influence: f64,
    pub stubbornness: f64,
    pub forum: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AgentSpec {
    pub key: String,
    pub name: String,
    pub role: String,
    #[serde(default)]
    pub entity: Option<String>,
    pub traits: Traits,
    #[serde(default)]
    pub follows: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EventSpec {
    pub round: u16,
    pub title: String,
    pub shift: f64,
    pub reach: f64,
    #[serde(default)]
    pub target: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ScenarioSpec {
    pub title: String,
    pub question: String,
    pub seed: u64,
    pub rounds: u16,
    #[serde(default)]
    pub entities: Vec<EntitySpec>,
    #[serde(default)]
    pub relations: Vec<RelationSpec>,
    pub agents: Vec<AgentSpec>,
    #[serde(default)]
    pub events: Vec<EventSpec>,
}

fn invalid(field: &'static str, reason: &'static str) -> ForesightError {
    ForesightError::Invalid { field, reason }
}

pub(crate) fn key(field: &'static str, value: &str) -> Result<(), ForesightError> {
    let mut chars = value.chars();
    let head = chars
        .next()
        .is_some_and(|c| c.is_ascii_lowercase() || c.is_ascii_digit());
    let tail = chars.all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_' || c == '-');
    if head && tail && value.len() <= MAX_KEY {
        Ok(())
    } else {
        Err(invalid(field, "key must match [a-z0-9][a-z0-9_-]{0,63}"))
    }
}

fn forbidden(c: char, multiline: bool) -> bool {
    (c.is_control() && !(multiline && c == '\n'))
        || matches!(c, '\u{200E}' | '\u{200F}' | '\u{202A}'..='\u{202E}' | '\u{2066}'..='\u{2069}')
}

pub(crate) fn text(
    field: &'static str,
    value: &str,
    max: usize,
    multiline: bool,
) -> Result<(), ForesightError> {
    if value.trim().is_empty() {
        return Err(invalid(field, "empty"));
    }
    if value.chars().count() > max {
        return Err(invalid(field, "too long"));
    }
    if value.chars().any(|c| forbidden(c, multiline)) {
        return Err(invalid(field, "forbidden character"));
    }
    Ok(())
}

fn within(field: &'static str, value: f64, low: f64, high: f64) -> Result<(), ForesightError> {
    if value.is_finite() && (low..=high).contains(&value) {
        Ok(())
    } else {
        Err(invalid(field, "out of range"))
    }
}

impl Traits {
    pub fn validate(&self) -> Result<(), ForesightError> {
        within("stance", self.stance, -1.0, 1.0)?;
        within("openness", self.openness, 0.0, 1.0)?;
        within("activity", self.activity, 0.0, 1.0)?;
        within("influence", self.influence, 0.0, 1.0)?;
        within("stubbornness", self.stubbornness, 0.0, 1.0)?;
        within("forum", self.forum, 0.0, 1.0)
    }
}

impl EventSpec {
    pub fn validate(&self, rounds: u16) -> Result<(), ForesightError> {
        if self.round == 0 || self.round > rounds {
            return Err(invalid("event round", "outside the simulation"));
        }
        text("event title", &self.title, MAX_NAME, false)?;
        within("event shift", self.shift, -1.0, 1.0)?;
        within("event reach", self.reach, 0.0, 1.0)?;
        if let Some(target) = &self.target {
            key("event target", target)?;
        }
        Ok(())
    }
}

fn unique<'a>(
    field: &'static str,
    keys: impl Iterator<Item = &'a str>,
) -> Result<BTreeSet<&'a str>, ForesightError> {
    let mut seen = BTreeSet::new();
    for value in keys {
        key(field, value)?;
        if !seen.insert(value) {
            return Err(ForesightError::Duplicate(field));
        }
    }
    Ok(seen)
}

impl ScenarioSpec {
    pub fn validate(&self) -> Result<(), ForesightError> {
        text("title", &self.title, MAX_NAME, false)?;
        text("question", &self.question, MAX_TEXT, true)?;
        if self.rounds == 0 || self.rounds > MAX_ROUNDS {
            return Err(ForesightError::Limit("rounds"));
        }
        if self.agents.len() < 2 || self.agents.len() > MAX_AGENTS {
            return Err(ForesightError::Limit("agents"));
        }
        if self.entities.len() > MAX_ENTITIES {
            return Err(ForesightError::Limit("entities"));
        }
        if self.relations.len() > MAX_RELATIONS {
            return Err(ForesightError::Limit("relations"));
        }
        if self.events.len() > MAX_EVENTS {
            return Err(ForesightError::Limit("events"));
        }
        let entities = unique("entities", self.entities.iter().map(|e| e.key.as_str()))?;
        for entity in &self.entities {
            text("entity name", &entity.name, MAX_NAME, false)?;
            text("entity kind", &entity.kind, MAX_LABEL, false)?;
        }
        for relation in &self.relations {
            if !entities.contains(relation.from.as_str())
                || !entities.contains(relation.to.as_str())
            {
                return Err(ForesightError::Unknown("relations"));
            }
            if relation.from == relation.to {
                return Err(invalid("relation", "an entity cannot relate to itself"));
            }
            text("relation kind", &relation.kind, MAX_LABEL, false)?;
            within("relation weight", relation.weight, -1.0, 1.0)?;
        }
        let agents = unique("agents", self.agents.iter().map(|a| a.key.as_str()))?;
        for agent in &self.agents {
            text("agent name", &agent.name, MAX_NAME, false)?;
            text("agent role", &agent.role, MAX_LABEL, false)?;
            agent.traits.validate()?;
            if agent
                .entity
                .as_deref()
                .is_some_and(|e| !entities.contains(e))
            {
                return Err(ForesightError::Unknown("agent entity"));
            }
            if agent.follows.len() > MAX_FOLLOWS {
                return Err(ForesightError::Limit("follows"));
            }
            for target in &agent.follows {
                if !agents.contains(target.as_str()) || *target == agent.key {
                    return Err(ForesightError::Unknown("follows"));
                }
            }
        }
        for event in &self.events {
            event.validate(self.rounds)?;
            if event
                .target
                .as_deref()
                .is_some_and(|t| !entities.contains(t))
            {
                return Err(ForesightError::Unknown("event target"));
            }
        }
        Ok(())
    }
}
