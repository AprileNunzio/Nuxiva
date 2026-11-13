use std::collections::HashMap;

use serde::{Deserialize, Serialize};
use sha2::{Digest as _, Sha256};

use super::ident::{Digest, Ident};
use super::{Validate, version};
use crate::error::{SwarmError, SwarmResult};
use crate::settings::Settings;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StepBudget {
    pub tokens: u64,
    pub tool_calls: u64,
    pub time_ms: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum VerifySpec {
    None,
    Judge,
    Evidence,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Step {
    pub id: Ident,
    pub worker_template: Ident,
    pub intent: Ident,
    pub goal_ref: Ident,
    pub needs_graph: bool,
    pub budget: StepBudget,
    pub verify: VerifySpec,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Edge {
    pub from: Ident,
    pub to: Ident,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Plan {
    pub schema_version: u32,
    pub id: Ident,
    pub steps: Vec<Step>,
    #[serde(default)]
    pub edges: Vec<Edge>,
}

impl Plan {
    pub fn digest(&self) -> SwarmResult<Digest> {
        let bytes = serde_json::to_vec(self).map_err(|_| SwarmError::Serialize)?;
        let hash = Sha256::digest(bytes);
        let mut hex = String::with_capacity(64);
        for byte in hash {
            hex.push(char::from_digit(u32::from(byte >> 4), 16).unwrap_or('0'));
            hex.push(char::from_digit(u32::from(byte & 0x0f), 16).unwrap_or('0'));
        }
        Ok(Digest::from_hex(hex))
    }

    fn index(&self) -> SwarmResult<HashMap<&str, usize>> {
        let mut index = HashMap::with_capacity(self.steps.len());
        for (position, step) in self.steps.iter().enumerate() {
            if index.insert(step.id.as_str(), position).is_some() {
                return Err(SwarmError::Invalid);
            }
        }
        Ok(index)
    }

    fn ensure_acyclic(&self, index: &HashMap<&str, usize>) -> SwarmResult<()> {
        let mut indegree = vec![0_usize; self.steps.len()];
        let mut next: Vec<Vec<usize>> = vec![Vec::new(); self.steps.len()];
        for edge in &self.edges {
            let (Some(&from), Some(&to)) =
                (index.get(edge.from.as_str()), index.get(edge.to.as_str()))
            else {
                return Err(SwarmError::Invalid);
            };
            if from == to {
                return Err(SwarmError::Cycle);
            }
            if let Some(slot) = next.get_mut(from) {
                slot.push(to);
            }
            if let Some(slot) = indegree.get_mut(to) {
                *slot = slot.saturating_add(1);
            }
        }
        let mut ready: Vec<usize> = indegree
            .iter()
            .enumerate()
            .filter_map(|(i, d)| (*d == 0).then_some(i))
            .collect();
        let mut visited = 0_usize;
        while let Some(node) = ready.pop() {
            visited = visited.saturating_add(1);
            for &target in next.get(node).map_or(&[][..], Vec::as_slice) {
                if let Some(slot) = indegree.get_mut(target) {
                    *slot = slot.saturating_sub(1);
                    if *slot == 0 {
                        ready.push(target);
                    }
                }
            }
        }
        if visited == self.steps.len() {
            Ok(())
        } else {
            Err(SwarmError::Cycle)
        }
    }
}

impl Validate for StepBudget {
    fn validate(&self, settings: &Settings) -> SwarmResult<()> {
        let ok = (1..=settings.max_tokens).contains(&self.tokens)
            && (1..=settings.max_tool_calls).contains(&self.tool_calls)
            && (1..=settings.max_time_ms).contains(&self.time_ms);
        if ok { Ok(()) } else { Err(SwarmError::Budget) }
    }
}

impl Validate for Plan {
    fn validate(&self, settings: &Settings) -> SwarmResult<()> {
        version(self.schema_version)?;
        if self.steps.is_empty() || self.steps.len() > settings.max_steps {
            return Err(SwarmError::TooLarge);
        }
        if self.edges.len() > settings.max_edges {
            return Err(SwarmError::TooLarge);
        }
        for step in &self.steps {
            step.budget.validate(settings)?;
        }
        let index = self.index()?;
        self.ensure_acyclic(&index)
    }
}
