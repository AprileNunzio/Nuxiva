use serde::{Deserialize, Serialize};

use super::glob::glob_match;
use super::risk::Risk;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Scope {
    pub servers: Vec<String>,
    pub tools: Vec<String>,
    pub max_risk: Risk,
}

impl Scope {
    #[must_use]
    pub fn none() -> Self {
        Self {
            servers: Vec::new(),
            tools: Vec::new(),
            max_risk: Risk::Info,
        }
    }

    #[must_use]
    pub fn permits(&self, server: &str, tool_id: &str, risk: Risk) -> bool {
        risk <= self.max_risk
            && self.servers.iter().any(|p| glob_match(p, server))
            && self.tools.iter().any(|p| glob_match(p, tool_id))
    }
}
