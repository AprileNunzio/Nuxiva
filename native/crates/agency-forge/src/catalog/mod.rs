use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::error::ForgeError;
use crate::manifest::{ForgedToolRecord, ForgedToolSpec, ToolStatus};

pub const MAX_CATALOG_TOOLS: usize = 512;
pub const AUTO_QUARANTINE_FAILURES: u64 = 3;

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ForgeCatalog {
    tools: BTreeMap<String, ForgedToolRecord>,
}

impl ForgeCatalog {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.tools.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.tools.is_empty()
    }

    pub fn propose(&mut self, spec: ForgedToolSpec) -> Result<ForgedToolRecord, ForgeError> {
        let next_version = self
            .tools
            .get(spec.name.trim().trim_start_matches("x_"))
            .map_or(1, |prev| prev.version.saturating_add(1));

        if next_version == 1 && self.tools.len() >= MAX_CATALOG_TOOLS {
            return Err(ForgeError::CapacityReached(MAX_CATALOG_TOOLS));
        }

        let record = ForgedToolRecord::from_spec(spec, next_version)?;
        self.tools.insert(record.name.clone(), record.clone());
        Ok(record)
    }

    pub fn approve(&mut self, name: &str) -> Result<ForgedToolRecord, ForgeError> {
        let key = name.trim().trim_start_matches("x_");
        let tool = self
            .tools
            .get_mut(key)
            .ok_or_else(|| ForgeError::NotFound(key.to_owned()))?;
        tool.approved = true;
        tool.status = ToolStatus::Active;
        Ok(tool.clone())
    }

    pub fn revoke(&mut self, name: &str, reason: &str) -> Result<ForgedToolRecord, ForgeError> {
        let key = name.trim().trim_start_matches("x_");
        let tool = self
            .tools
            .get_mut(key)
            .ok_or_else(|| ForgeError::NotFound(key.to_owned()))?;
        tool.approved = false;
        tool.status = ToolStatus::Revoked;
        tool.last_error = Some(reason.chars().take(300).collect());
        Ok(tool.clone())
    }

    pub fn record_execution(
        &mut self,
        name: &str,
        ok: bool,
        error: Option<&str>,
    ) -> Result<ForgedToolRecord, ForgeError> {
        let key = name.trim().trim_start_matches("x_");
        let tool = self
            .tools
            .get_mut(key)
            .ok_or_else(|| ForgeError::NotFound(key.to_owned()))?;
        if !tool.is_callable() {
            return Err(ForgeError::NotCallable(tool.call_name.clone()));
        }
        tool.invocations = tool.invocations.saturating_add(1);
        if ok {
            tool.last_error = None;
        } else {
            tool.failures = tool.failures.saturating_add(1);
            tool.last_error = error.map(|e| e.chars().take(300).collect());
            if tool.failures >= AUTO_QUARANTINE_FAILURES {
                tool.status = ToolStatus::Quarantined;
                tool.approved = false;
            }
        }
        Ok(tool.clone())
    }

    #[must_use]
    pub fn get(&self, name: &str) -> Option<&ForgedToolRecord> {
        let key = name.trim().trim_start_matches("x_");
        self.tools.get(key)
    }

    #[must_use]
    pub fn active_tools(&self) -> Vec<&ForgedToolRecord> {
        self.tools.values().filter(|t| t.is_callable()).collect()
    }
}
