use std::collections::BTreeMap;

use crate::error::{RouteError, RouteResult};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Task {
    Understand,
    Plan,
    Summarize,
    Generate,
    Code,
    Vision,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Sensitivity {
    Public,
    Private,
    Secret,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Placement {
    Local,
    Cloud,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Profile {
    pub id: String,
    pub placement: Placement,
    pub context_tokens: u32,
    pub micro_per_1k_in: u32,
    pub micro_per_1k_out: u32,
    pub latency_ms: u32,
    pub quality_bps: BTreeMap<Task, u16>,
}

impl Profile {
    pub fn validate(&self) -> RouteResult<()> {
        let named = !self.id.is_empty()
            && self.id.len() <= 64
            && self
                .id
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'-' | b'_' | b':'));
        if !named {
            return Err(RouteError::Invalid("id"));
        }
        if self.context_tokens == 0 || self.quality_bps.values().any(|q| *q > 10_000) {
            return Err(RouteError::Invalid("profile"));
        }
        if self.placement == Placement::Local
            && (self.micro_per_1k_in != 0 || self.micro_per_1k_out != 0)
        {
            return Err(RouteError::Invalid("local_cost"));
        }
        Ok(())
    }

    #[must_use]
    pub fn quality(&self, task: Task) -> u16 {
        self.quality_bps.get(&task).copied().unwrap_or(0)
    }

    #[must_use]
    pub fn cost(&self, input: u32, output: u32) -> u64 {
        let side =
            |tokens: u32, rate: u32| u64::from(tokens).saturating_mul(u64::from(rate)) / 1000;
        side(input, self.micro_per_1k_in).saturating_add(side(output, self.micro_per_1k_out))
    }
}
