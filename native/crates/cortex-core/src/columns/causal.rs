use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConditionalProbabilityTable {
    pub variable: String,
    pub parents: Vec<String>,
    pub probabilities: BTreeMap<String, f64>,
}

impl ConditionalProbabilityTable {
    #[must_use]
    pub fn new(variable: &str, parents: Vec<String>) -> Self {
        Self {
            variable: variable.to_string(),
            parents,
            probabilities: BTreeMap::new(),
        }
    }

    pub fn set_prob(&mut self, state_key: &str, p: f64) {
        self.probabilities
            .insert(state_key.to_string(), p.clamp(0.0, 1.0));
    }

    #[must_use]
    pub fn get_prob(&self, state_key: &str) -> f64 {
        self.probabilities.get(state_key).copied().unwrap_or(0.5)
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct CausalGraph {
    nodes: BTreeSet<String>,
    edges: BTreeMap<String, BTreeSet<String>>,
    tables: BTreeMap<String, ConditionalProbabilityTable>,
}

impl CausalGraph {
    #[must_use]
    pub fn new() -> Self {
        Self {
            nodes: BTreeSet::new(),
            edges: BTreeMap::new(),
            tables: BTreeMap::new(),
        }
    }

    pub fn add_node(&mut self, name: &str) {
        self.nodes.insert(name.to_string());
        self.edges.entry(name.to_string()).or_default();
    }

    pub fn add_directed_edge(&mut self, from: &str, to: &str) {
        self.add_node(from);
        self.add_node(to);
        self.edges
            .entry(from.to_string())
            .or_default()
            .insert(to.to_string());
    }

    pub fn set_cpt(&mut self, table: ConditionalProbabilityTable) {
        self.tables.insert(table.variable.clone(), table);
    }

    #[must_use]
    pub fn parents_of(&self, node: &str) -> Vec<String> {
        let mut parents = Vec::new();
        for (parent, children) in &self.edges {
            if children.contains(node) {
                parents.push(parent.clone());
            }
        }
        parents
    }

    #[must_use]
    pub fn observe(&self, target: &str, condition_var: &str, condition_val: bool) -> f64 {
        let key = format!(
            "{}_{}",
            condition_var,
            if condition_val { "1" } else { "0" }
        );
        if let Some(table) = self.tables.get(target) {
            table.get_prob(&key)
        } else {
            0.5
        }
    }

    #[must_use]
    pub fn do_intervention(&self, target: &str, intervened_var: &str, intervened_val: bool) -> f64 {
        let mut mutilated = self.clone();
        for children in mutilated.edges.values_mut() {
            children.remove(intervened_var);
        }
        mutilated.observe(target, intervened_var, intervened_val)
    }

    #[must_use]
    pub fn counterfactual(
        &self,
        target: &str,
        factual_var: &str,
        factual_val: bool,
        counterfactual_val: bool,
    ) -> f64 {
        let factual_p = self.observe(target, factual_var, factual_val);
        let counterfactual_p = self.do_intervention(target, factual_var, counterfactual_val);
        (counterfactual_p * 0.7 + (1.0 - factual_p) * 0.3).clamp(0.0, 1.0)
    }
}
