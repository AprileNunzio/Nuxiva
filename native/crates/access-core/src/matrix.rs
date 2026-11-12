use crate::capability::Capability;
use crate::cell::Cell;
use crate::error::AccessError;
use crate::floor::harden;
use crate::role::{COLUMNS, Role};
use serde::Deserialize;
use std::collections::BTreeMap;

pub const DEFAULT_JSON: &str = include_str!("matrix/default.json");
pub const MAX_MATRIX: usize = 256 * 1024;
pub const MAX_RULES: usize = 1024;
pub const FALLBACK: &str = "risk.critical";
const VERSION: u32 = 1;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Raw {
    version: u32,
    rules: BTreeMap<String, Vec<String>>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Matrix {
    rules: BTreeMap<String, [Cell; COLUMNS]>,
}

fn pattern(raw: &str) -> Result<(), AccessError> {
    match raw.strip_suffix(".*") {
        Some(prefix) if !prefix.contains('*') => {
            let probe = format!("{prefix}.x");
            Capability::parse(&probe).map(|_| ())
        }
        Some(_) => Err(AccessError::Capability),
        None => Capability::parse(raw).map(|_| ()),
    }
}

fn row(values: &[String]) -> Result<[Cell; COLUMNS], AccessError> {
    if values.len() != COLUMNS {
        return Err(AccessError::Schema);
    }
    let mut cells = [Cell::Deny; COLUMNS];
    for (slot, value) in cells.iter_mut().zip(values) {
        *slot = Cell::parse(value)?;
    }
    Ok(cells)
}

impl Matrix {
    pub fn parse(raw: &str) -> Result<Self, AccessError> {
        if raw.len() > MAX_MATRIX {
            return Err(AccessError::TooLarge);
        }
        let data: Raw = serde_json::from_str(raw).map_err(|_| AccessError::Schema)?;
        if data.version != VERSION {
            return Err(AccessError::Version);
        }
        if data.rules.len() > MAX_RULES || !data.rules.contains_key(FALLBACK) {
            return Err(AccessError::Schema);
        }
        let mut rules = BTreeMap::new();
        for (key, values) in &data.rules {
            pattern(key)?;
            rules.insert(key.clone(), harden(key, row(values)?));
        }
        Ok(Self { rules })
    }

    pub fn builtin() -> Result<Self, AccessError> {
        Self::parse(DEFAULT_JSON)
    }

    #[must_use]
    pub fn cell(&self, capability: &Capability, role: Role) -> Cell {
        let Some(column) = role.column() else {
            return Cell::Allow;
        };
        let row = capability
            .candidates()
            .iter()
            .find_map(|key| self.rules.get(key))
            .or_else(|| self.rules.get(FALLBACK));
        row.and_then(|cells| cells.get(column).copied())
            .unwrap_or(Cell::Deny)
    }

    #[must_use]
    pub fn export(&self) -> BTreeMap<String, Vec<&'static str>> {
        self.rules
            .iter()
            .map(|(k, cells)| (k.clone(), cells.iter().map(|c| c.name()).collect()))
            .collect()
    }
}
