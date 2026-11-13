use std::sync::PoisonError;

use serde::Serialize;
use serde_json::Value;

use super::Hub;
use crate::policy::Risk;

#[derive(Debug, Clone, Serialize)]
pub struct ToolView {
    pub id: String,
    pub server: String,
    pub name: String,
    pub title: Option<String>,
    pub description: Option<String>,
    pub input_schema: Value,
    pub risk: Risk,
    pub state: &'static str,
    pub hash: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ServerView {
    pub id: String,
    pub health: &'static str,
    pub tools: usize,
    pub attempts: u32,
    pub last_error: Option<&'static str>,
    pub max_risk: Risk,
}

impl Hub {
    #[must_use]
    pub fn tools(&self) -> Vec<ToolView> {
        self.registry
            .snapshot()
            .iter()
            .map(|entry| ToolView {
                id: entry.id.clone(),
                server: entry.server.clone(),
                name: entry.remote_name.clone(),
                title: entry.spec.title.clone(),
                description: entry.spec.description.clone(),
                input_schema: entry.spec.input_schema.clone(),
                risk: entry.risk,
                state: entry.state.as_str(),
                hash: entry.hash.clone(),
            })
            .collect()
    }

    #[must_use]
    pub fn statuses(&self) -> Vec<ServerView> {
        let servers = self.servers.lock().unwrap_or_else(PoisonError::into_inner);
        let mut views: Vec<ServerView> = servers
            .iter()
            .map(|(id, running)| {
                let status = *running.handle.status.borrow();
                ServerView {
                    id: id.clone(),
                    health: status.health.as_str(),
                    tools: status.tools,
                    attempts: status.attempts,
                    last_error: status.last_error.map(crate::McpError::code),
                    max_risk: running.entry.max_risk,
                }
            })
            .collect();
        views.sort_by(|a, b| a.id.cmp(&b.id));
        views
    }

    #[must_use]
    pub fn tools_version(&self) -> u64 {
        self.registry.version()
    }
}
