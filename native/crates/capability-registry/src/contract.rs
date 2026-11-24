use std::collections::BTreeSet;

use serde::{Deserialize, Serialize};

use crate::error::{RegistryError, RegistryResult};
use crate::types::{Effect, Origin, Role, State, ValueType};

pub const MAX_ID_BYTES: usize = 64;
pub const MAX_SUMMARY_BYTES: usize = 240;
pub const MAX_SUMMARY_TOKENS: usize = 60;
pub const MAX_INPUTS: usize = 24;
pub const MAX_TAGS: usize = 12;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Param {
    pub name: String,
    pub ty: ValueType,
    pub required: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Contract {
    pub id: String,
    pub version: u32,
    pub origin: Origin,
    pub summary: String,
    pub inputs: Vec<Param>,
    pub output: ValueType,
    pub effects: BTreeSet<Effect>,
    pub reversible: bool,
    pub min_role: Role,
    pub nodes: BTreeSet<String>,
    #[serde(default)]
    pub tags: BTreeSet<String>,
    #[serde(default = "default_state")]
    pub state: State,
}

fn default_state() -> State {
    State::Active
}

#[must_use]
pub fn token_estimate(text: &str) -> usize {
    text.len().div_ceil(4)
}

fn slug(text: &str, max: usize) -> bool {
    !text.is_empty()
        && text.len() <= max
        && text
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_' || b == b'.')
}

impl Contract {
    pub fn validate(&self) -> RegistryResult<()> {
        if !slug(&self.id, MAX_ID_BYTES) {
            return Err(RegistryError::Invalid("id"));
        }
        if self.version == 0 {
            return Err(RegistryError::Invalid("version"));
        }
        if self.summary.trim().is_empty()
            || self.summary.len() > MAX_SUMMARY_BYTES
            || token_estimate(&self.summary) > MAX_SUMMARY_TOKENS
            || self.summary.chars().any(char::is_control)
        {
            return Err(RegistryError::Invalid("summary"));
        }
        if self.inputs.len() > MAX_INPUTS {
            return Err(RegistryError::Invalid("inputs"));
        }
        let mut names = BTreeSet::new();
        for param in &self.inputs {
            if !slug(&param.name, MAX_ID_BYTES) || !names.insert(param.name.as_str()) {
                return Err(RegistryError::Invalid("input_name"));
            }
        }
        if self.effects.is_empty() {
            return Err(RegistryError::Invalid("effects"));
        }
        if self.reversible
            && self
                .effects
                .iter()
                .any(|e| e.irreversible_risk() && *e != Effect::Physical)
        {
            return Err(RegistryError::Invalid("reversible"));
        }
        if self.nodes.is_empty() || self.nodes.iter().any(|n| !slug(n, MAX_ID_BYTES)) {
            return Err(RegistryError::Invalid("nodes"));
        }
        if self.tags.len() > MAX_TAGS || self.tags.iter().any(|t| !slug(t, MAX_ID_BYTES)) {
            return Err(RegistryError::Invalid("tags"));
        }
        Ok(())
    }

    #[must_use]
    pub fn requires_approval(&self) -> bool {
        !self.reversible
            || self
                .effects
                .iter()
                .any(|e| e.irreversible_risk() && *e != Effect::Physical)
    }
}
