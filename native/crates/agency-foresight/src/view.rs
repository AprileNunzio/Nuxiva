use serde::{Deserialize, Serialize};

use crate::agent::{AgentStats, Recall};
use crate::error::ForesightError;
use crate::num::round3;
use crate::spec::Traits;
use crate::world::World;

const FOLLOW_PREVIEW: usize = 24;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MemoryView {
    pub round: u16,
    pub kind: Recall,
    pub other: Option<String>,
    pub event: Option<String>,
    pub stance: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AgentView {
    pub key: String,
    pub name: String,
    pub role: String,
    pub entity: Option<String>,
    pub traits: Traits,
    pub stance: f64,
    pub initial: f64,
    pub follows: Vec<String>,
    pub followers: u32,
    pub stats: AgentStats,
    pub memory: Vec<MemoryView>,
}

impl World {
    fn name_of(&self, agent: usize) -> Option<String> {
        self.state.spec.agents.get(agent).map(|a| a.name.clone())
    }

    pub fn agent(&self, key: &str) -> Result<AgentView, ForesightError> {
        let index = self.topo.agent(key).ok_or(ForesightError::AgentNotFound)?;
        let spec = self
            .state
            .spec
            .agents
            .get(index)
            .ok_or(ForesightError::AgentNotFound)?;
        let state = self
            .state
            .agents
            .get(index)
            .ok_or(ForesightError::AgentNotFound)?;
        let entity = self
            .topo
            .entity_of(index)
            .and_then(|e| self.state.spec.entities.get(e))
            .map(|e| e.name.clone());
        let memory = state
            .memory
            .iter()
            .map(|m| MemoryView {
                round: m.round,
                kind: m.kind,
                other: m.other.and_then(|o| self.name_of(o)),
                event: m
                    .event
                    .and_then(|e| self.state.spec.events.get(e))
                    .map(|e| e.title.clone()),
                stance: round3(m.stance),
            })
            .collect();
        Ok(AgentView {
            key: spec.key.clone(),
            name: spec.name.clone(),
            role: spec.role.clone(),
            entity,
            traits: spec.traits,
            stance: round3(state.stance),
            initial: round3(state.initial),
            follows: state
                .follows
                .iter()
                .take(FOLLOW_PREVIEW)
                .filter_map(|&f| self.name_of(f))
                .collect(),
            followers: self.followers().get(index).copied().unwrap_or(0),
            stats: state.stats,
            memory,
        })
    }
}
