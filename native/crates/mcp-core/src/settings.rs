use serde::{Deserialize, Serialize};

use crate::error::{McpError, McpResult};
use crate::limits::Ceilings;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Settings {
    pub max_message_bytes: usize,
    pub max_pages: usize,
    pub max_tools_per_server: usize,
    pub max_tools_total: usize,
    pub max_name_len: usize,
    pub max_description_chars: usize,
    pub max_schema_bytes: usize,
    pub max_schema_depth: usize,
    pub max_schema_nodes: usize,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            max_message_bytes: 1024 * 1024,
            max_pages: 50,
            max_tools_per_server: 500,
            max_tools_total: 5_000,
            max_name_len: 64,
            max_description_chars: 1_000,
            max_schema_bytes: 64 * 1024,
            max_schema_depth: 24,
            max_schema_nodes: 20_000,
        }
    }
}

fn within(value: usize, ceiling: usize) -> McpResult<()> {
    if (1..=ceiling).contains(&value) {
        Ok(())
    } else {
        Err(McpError::InvalidSettings)
    }
}

impl Settings {
    pub fn from_json(text: &str) -> McpResult<Self> {
        let settings: Self = serde_json::from_str(text).map_err(|_| McpError::InvalidSettings)?;
        settings.validate()?;
        Ok(settings)
    }

    pub fn validate(&self) -> McpResult<()> {
        within(self.max_message_bytes, Ceilings::MESSAGE_BYTES)?;
        within(self.max_pages, Ceilings::PAGES)?;
        within(self.max_tools_per_server, Ceilings::TOOLS_PER_SERVER)?;
        within(self.max_tools_total, Ceilings::TOOLS_TOTAL)?;
        within(self.max_name_len, Ceilings::NAME_LEN)?;
        within(self.max_description_chars, Ceilings::DESCRIPTION_CHARS)?;
        within(self.max_schema_bytes, Ceilings::SCHEMA_BYTES)?;
        within(self.max_schema_depth, Ceilings::SCHEMA_DEPTH)?;
        within(self.max_schema_nodes, Ceilings::SCHEMA_NODES)?;
        if self.max_tools_per_server > self.max_tools_total {
            return Err(McpError::InvalidSettings);
        }
        Ok(())
    }
}
