use serde::Serialize;

use super::Hub;

#[derive(Debug, Clone, Serialize)]
pub struct Metrics {
    pub schema_version: u32,
    pub servers: usize,
    pub healthy: usize,
    pub tools: usize,
    pub active: usize,
    pub pending_approval: usize,
    pub quarantined_servers: usize,
    pub running_jobs: usize,
    pub tools_version: u64,
}

impl Hub {
    #[must_use]
    pub fn metrics(&self) -> Metrics {
        let tools = self.tools();
        let statuses = self.statuses();
        Metrics {
            schema_version: 1,
            servers: statuses.len(),
            healthy: statuses.iter().filter(|s| s.health == "ready").count(),
            tools: tools.len(),
            active: tools.iter().filter(|t| t.state == "active").count(),
            pending_approval: tools.iter().filter(|t| t.state != "active").count(),
            quarantined_servers: self.quarantined().len(),
            running_jobs: self.running_jobs(),
            tools_version: self.tools_version(),
        }
    }
}
