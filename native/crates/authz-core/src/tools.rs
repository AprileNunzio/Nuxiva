use std::collections::{BTreeSet, HashMap};

use crate::levels::Risk;

pub const MAX_TOOLS: usize = 8192;
pub const MAX_STEPS: usize = 64;
const MAX_DEPTH: usize = 32;

#[derive(Debug, Clone, Default)]
pub struct RiskTable {
    tools: HashMap<String, Risk>,
    composed: HashMap<String, Vec<String>>,
}

impl RiskTable {
    #[must_use]
    pub fn new(tools: HashMap<String, Risk>) -> Self {
        Self {
            tools,
            composed: HashMap::new(),
        }
    }

    pub fn set(&mut self, name: &str, risk: Risk) -> bool {
        if !self.tools.contains_key(name) && self.tools.len() >= MAX_TOOLS {
            return false;
        }
        self.tools.insert(name.to_owned(), risk);
        true
    }

    pub fn compose(&mut self, name: &str, steps: Vec<String>) -> bool {
        if steps.len() > MAX_STEPS
            || (!self.composed.contains_key(name) && self.composed.len() >= MAX_TOOLS)
        {
            return false;
        }
        self.composed.insert(name.to_owned(), steps);
        true
    }

    pub fn forget(&mut self, name: &str) {
        self.composed.remove(name);
    }

    fn resolve(&self, name: &str, seen: &mut BTreeSet<String>, depth: usize) -> Risk {
        if let Some(risk) = self.tools.get(name) {
            return *risk;
        }
        let Some(steps) = self.composed.get(name) else {
            return Risk::Critical;
        };
        if steps.is_empty() || seen.contains(name) || depth >= MAX_DEPTH {
            return Risk::Critical;
        }
        seen.insert(name.to_owned());
        let worst = steps
            .iter()
            .map(|step| self.resolve(step, seen, depth.saturating_add(1)))
            .max()
            .unwrap_or(Risk::Critical);
        seen.remove(name);
        worst
    }

    #[must_use]
    pub fn of_tool(&self, name: &str) -> Risk {
        self.resolve(name, &mut BTreeSet::new(), 0)
    }
}
