use serde::{Deserialize, Serialize};

use crate::error::{ContextError, ContextResult};
use crate::policy::Policy;

pub const CEIL_PERSONS: usize = 100_000;
pub const CEIL_LIST: usize = 256;
pub const CEIL_TEXT: usize = 4_000;
pub const CEIL_BUDGET: usize = 64_000;
pub const CEIL_CACHE: usize = 4_096;
pub const CEIL_MS: u64 = 604_800_000;
pub const CEIL_SEALED: usize = 64 * 1024;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct ContextSettings {
    pub max_persons: usize,
    pub max_list_items: usize,
    pub max_text_chars: usize,
    pub max_relations: usize,
    pub max_listening: usize,
    pub max_sealed_bytes: usize,
    pub render_cache_entries: usize,
    pub default_budget_chars: usize,
    pub max_budget_chars: usize,
    pub affect_half_life_ms: u64,
    pub affect_max_age_ms: u64,
    pub cache_bucket_ms: u64,
    pub policy: Policy,
}

impl Default for ContextSettings {
    fn default() -> Self {
        Self {
            max_persons: 1_000,
            max_list_items: 16,
            max_text_chars: 400,
            max_relations: 16,
            max_listening: 20,
            max_sealed_bytes: 4 * 1024,
            render_cache_entries: 64,
            default_budget_chars: 2_000,
            max_budget_chars: 16_000,
            affect_half_life_ms: 1_800_000,
            affect_max_age_ms: 7_200_000,
            cache_bucket_ms: 60_000,
            policy: Policy::default(),
        }
    }
}

fn within(value: usize, ceiling: usize) -> bool {
    (1..=ceiling).contains(&value)
}

fn within_ms(value: u64) -> bool {
    (1..=CEIL_MS).contains(&value)
}

impl ContextSettings {
    pub fn validate(&self) -> ContextResult<()> {
        let ok = within(self.max_persons, CEIL_PERSONS)
            && within(self.max_list_items, CEIL_LIST)
            && within(self.max_text_chars, CEIL_TEXT)
            && within(self.max_relations, CEIL_LIST)
            && within(self.max_listening, CEIL_LIST)
            && within(self.max_sealed_bytes, CEIL_SEALED)
            && within(self.render_cache_entries, CEIL_CACHE)
            && within(self.max_budget_chars, CEIL_BUDGET)
            && within(self.default_budget_chars, self.max_budget_chars)
            && within_ms(self.affect_half_life_ms)
            && within_ms(self.affect_max_age_ms)
            && within_ms(self.cache_bucket_ms);
        if ok {
            Ok(())
        } else {
            Err(ContextError::Settings)
        }
    }

    pub fn from_json(raw: &str) -> ContextResult<Self> {
        if raw.len() > 256 * 1024 {
            return Err(ContextError::TooLarge);
        }
        let parsed: Self = serde_json::from_str(raw).map_err(|_| ContextError::Settings)?;
        parsed.validate()?;
        Ok(parsed)
    }
}
