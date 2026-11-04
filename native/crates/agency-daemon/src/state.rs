use agency_domain::{Project, Task};
use agency_planner::TaskGraph;
use agency_scheduler::{ModelProfile, Settings};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

use crate::error::AgencyError;

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EngineSettings {
    pub scheduler: Settings,
    pub model: ModelProfile,
}

impl Default for EngineSettings {
    fn default() -> Self {
        Self {
            scheduler: Settings::default(),
            model: ModelProfile::Local { size_mb: 4_700 },
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Snapshot {
    project: Project,
    tasks: Vec<Task>,
}

#[derive(Debug)]
pub struct ProjectState {
    pub project: Project,
    pub graph: TaskGraph,
}

impl ProjectState {
    pub fn encode(&self) -> Result<Vec<u8>, AgencyError> {
        let snapshot = Snapshot {
            project: self.project.clone(),
            tasks: self.graph.tasks().cloned().collect(),
        };
        Ok(serde_json::to_vec(&snapshot)?)
    }

    pub fn decode(bytes: &[u8]) -> Result<Self, AgencyError> {
        let snapshot: Snapshot = serde_json::from_slice(bytes)?;
        Ok(Self {
            project: snapshot.project,
            graph: TaskGraph::from_tasks(snapshot.tasks)?,
        })
    }

    #[must_use]
    pub fn summary(&self) -> Value {
        json!({
            "project": self.project,
            "progress": self.graph.progress(),
            "critical_path_seconds": self.graph.critical_path_seconds(),
        })
    }

    #[must_use]
    pub fn detail(&self) -> Value {
        let tasks: Vec<&Task> = self
            .graph
            .order()
            .into_iter()
            .filter_map(|id| self.graph.get(id))
            .collect();
        json!({
            "project": self.project,
            "progress": self.graph.progress(),
            "critical_path_seconds": self.graph.critical_path_seconds(),
            "ready": self.graph.ready(),
            "blocked": self.graph.blocked(),
            "tasks": tasks,
        })
    }
}
