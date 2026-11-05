use std::collections::{BTreeSet, VecDeque};

use serde::{Deserialize, Serialize};

pub const MEMORY: usize = 24;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Recall {
    Read,
    Liked,
    Replied,
    Reposted,
    Posted,
    Event,
    Followed,
    Unfollowed,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Memory {
    pub round: u16,
    pub kind: Recall,
    pub other: Option<usize>,
    pub event: Option<usize>,
    pub stance: f64,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AgentStats {
    pub posts: u32,
    pub replies: u32,
    pub reposts: u32,
    pub likes: u32,
    pub engagement: u32,
    pub reach: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AgentState {
    pub stance: f64,
    pub initial: f64,
    pub follows: BTreeSet<usize>,
    pub memory: VecDeque<Memory>,
    pub stats: AgentStats,
}

impl AgentState {
    #[must_use]
    pub fn new(stance: f64) -> Self {
        Self {
            stance,
            initial: stance,
            follows: BTreeSet::new(),
            memory: VecDeque::with_capacity(MEMORY),
            stats: AgentStats::default(),
        }
    }

    pub fn remember(&mut self, memory: Memory) {
        while self.memory.len() >= MEMORY {
            self.memory.pop_front();
        }
        self.memory.push_back(memory);
    }
}
