use std::collections::{BTreeMap, BTreeSet};

use capability_registry::{Effect, Role};
use serde::{Deserialize, Serialize};

use crate::error::{PolicyError, PolicyResult};

pub const MAX_POLICY_BYTES: usize = 128 * 1024;
pub const MAX_PATTERNS: usize = 256;

#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ContextRule {
    #[serde(default)]
    pub deny: Vec<String>,
    #[serde(default)]
    pub approve: Vec<String>,
    #[serde(default)]
    pub max_effects: Option<BTreeSet<Effect>>,
}

#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct UserRule {
    #[serde(default)]
    pub deny: Vec<String>,
    #[serde(default)]
    pub allow_only: Option<Vec<String>>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Policy {
    pub ceilings: BTreeMap<Role, BTreeSet<Effect>>,
    #[serde(default)]
    pub contexts: BTreeMap<String, ContextRule>,
    #[serde(default)]
    pub users: BTreeMap<String, UserRule>,
}

fn pattern_ok(pattern: &str) -> bool {
    let body = pattern.strip_suffix('*').unwrap_or(pattern);
    !pattern.is_empty()
        && pattern.len() <= 64
        && body
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_' || b == b'.')
}

fn slug(text: &str) -> bool {
    !text.is_empty()
        && text.len() <= 48
        && text
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_' || b == b'-')
}

#[must_use]
pub fn matches(pattern: &str, id: &str) -> bool {
    pattern
        .strip_suffix('*')
        .map_or_else(|| pattern == id, |prefix| id.starts_with(prefix))
}

impl Policy {
    pub fn parse(raw: &str) -> PolicyResult<Self> {
        if raw.len() > MAX_POLICY_BYTES {
            return Err(PolicyError::TooLarge);
        }
        let policy: Self = serde_json::from_str(raw).map_err(|_| PolicyError::Invalid("schema"))?;
        policy.validate()?;
        Ok(policy)
    }

    fn validate(&self) -> PolicyResult<()> {
        if !self.ceilings.contains_key(&Role::Guest) {
            return Err(PolicyError::Invalid("guest_ceiling"));
        }
        let mut previous: Option<&BTreeSet<Effect>> = None;
        for effects in self.ceilings.values() {
            if previous.is_some_and(|p| !p.is_subset(effects)) {
                return Err(PolicyError::Invalid("ceiling_order"));
            }
            previous = Some(effects);
        }
        let mut patterns = 0usize;
        for (name, rule) in &self.contexts {
            let listed = rule.deny.iter().chain(&rule.approve);
            patterns = patterns
                .saturating_add(rule.deny.len())
                .saturating_add(rule.approve.len());
            if !slug(name) || !listed.into_iter().all(|p| pattern_ok(p)) {
                return Err(PolicyError::Invalid("context"));
            }
        }
        for (user, rule) in &self.users {
            let allow = rule.allow_only.iter().flatten();
            patterns = patterns.saturating_add(rule.deny.len());
            if !slug(user) || !rule.deny.iter().chain(allow).all(|p| pattern_ok(p)) {
                return Err(PolicyError::Invalid("user"));
            }
        }
        if patterns > MAX_PATTERNS {
            return Err(PolicyError::TooLarge);
        }
        Ok(())
    }

    #[must_use]
    pub fn ceiling(&self, role: Role) -> BTreeSet<Effect> {
        self.ceilings
            .range(..=role)
            .next_back()
            .map(|(_, effects)| effects.clone())
            .unwrap_or_default()
    }
}
