use serde::{Deserialize, Serialize};

use crate::error::{BenchError, BenchResult};
use crate::observations::{SCHEMA, is_token};

pub const MAX_ENTRIES: usize = 100_000;
const GENESIS: &str = "0000000000000000000000000000000000000000000000000000000000000000";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    CiGreen,
    CiRed,
    ShadowClean,
    ShadowDivergent,
}

impl Kind {
    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            Self::CiGreen => "ci_green",
            Self::CiRed => "ci_red",
            Self::ShadowClean => "shadow_clean",
            Self::ShadowDivergent => "shadow_divergent",
        }
    }

    pub fn parse(value: &str) -> BenchResult<Self> {
        match value {
            "ci_green" => Ok(Self::CiGreen),
            "ci_red" => Ok(Self::CiRed),
            "shadow_clean" => Ok(Self::ShadowClean),
            "shadow_divergent" => Ok(Self::ShadowDivergent),
            _ => Err(BenchError::Invalid("ledger_kind")),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Entry {
    pub kind: Kind,
    pub id: String,
    pub day: u32,
    pub prev: String,
    pub hash: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Ledger {
    pub schema: u32,
    pub entries: Vec<Entry>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Criteria {
    pub min_days: u32,
    pub min_ci_green: u32,
    pub min_shadow_clean: u32,
}

impl Default for Criteria {
    fn default() -> Self {
        Self {
            min_days: 14,
            min_ci_green: 20,
            min_shadow_clean: 3,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Status {
    pub chain_ok: bool,
    pub observed_days: u32,
    pub ci_green_streak: u32,
    pub shadow_clean_streak: u32,
    pub missing: Vec<String>,
    pub ready: bool,
}

fn digest(kind: Kind, id: &str, day: u32, prev: &str) -> String {
    let mut hasher = blake3::Hasher::new();
    hasher.update(prev.as_bytes());
    hasher.update(&[0]);
    hasher.update(kind.name().as_bytes());
    hasher.update(&[0]);
    hasher.update(id.as_bytes());
    hasher.update(&[0]);
    hasher.update(&day.to_le_bytes());
    hasher.finalize().to_hex().to_string()
}

impl Default for Ledger {
    fn default() -> Self {
        Self {
            schema: SCHEMA,
            entries: Vec::new(),
        }
    }
}

impl Ledger {
    pub fn parse(bytes: &[u8]) -> BenchResult<Self> {
        let ledger: Self = serde_json::from_slice(bytes)?;
        if ledger.schema != SCHEMA {
            return Err(BenchError::Invalid("ledger_schema"));
        }
        if ledger.entries.len() > MAX_ENTRIES {
            return Err(BenchError::TooLarge("ledger"));
        }
        if !ledger.chain_ok() {
            return Err(BenchError::Corrupt("ledger_chain"));
        }
        Ok(ledger)
    }

    #[must_use]
    pub fn chain_ok(&self) -> bool {
        let mut prev = GENESIS;
        for e in &self.entries {
            if e.prev != prev || !is_token(&e.id) || e.hash != digest(e.kind, &e.id, e.day, &e.prev)
            {
                return false;
            }
            prev = &e.hash;
        }
        true
    }

    pub fn append(&mut self, kind: Kind, id: &str, day: u32) -> BenchResult<bool> {
        if !is_token(id) {
            return Err(BenchError::Invalid("ledger_id"));
        }
        if self.entries.len() >= MAX_ENTRIES {
            return Err(BenchError::TooLarge("ledger"));
        }
        if self.entries.iter().any(|e| e.kind == kind && e.id == id) {
            return Ok(false);
        }
        if self.entries.last().is_some_and(|e| day < e.day) {
            return Err(BenchError::Invalid("ledger_day_order"));
        }
        let prev = self
            .entries
            .last()
            .map_or_else(|| GENESIS.to_owned(), |e| e.hash.clone());
        let hash = digest(kind, id, day, &prev);
        self.entries.push(Entry {
            kind,
            id: id.to_owned(),
            day,
            prev,
            hash,
        });
        Ok(true)
    }

    #[must_use]
    pub fn status(&self, criteria: &Criteria, today: u32) -> Status {
        let chain_ok = self.chain_ok();
        let (mut ci, mut shadow) = (0u32, 0u32);
        for e in &self.entries {
            match e.kind {
                Kind::CiGreen => ci = ci.saturating_add(1),
                Kind::CiRed => ci = 0,
                Kind::ShadowClean => shadow = shadow.saturating_add(1),
                Kind::ShadowDivergent => shadow = 0,
            }
        }
        let first = self.entries.first().map_or(today, |e| e.day);
        let observed_days = today.saturating_sub(first);
        let mut missing = Vec::new();
        if !chain_ok {
            missing.push("chain".to_owned());
        }
        if observed_days < criteria.min_days {
            missing.push("days".to_owned());
        }
        if ci < criteria.min_ci_green {
            missing.push("ci_green".to_owned());
        }
        if shadow < criteria.min_shadow_clean {
            missing.push("shadow_clean".to_owned());
        }
        Status {
            chain_ok,
            observed_days,
            ci_green_streak: ci,
            shadow_clean_streak: shadow,
            ready: missing.is_empty(),
            missing,
        }
    }
}
