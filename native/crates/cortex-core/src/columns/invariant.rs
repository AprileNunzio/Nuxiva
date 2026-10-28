use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum TermPattern {
    Const(i64),
    FloatBits(u64),
    Var(String),
    Wildcard(usize),
    Compound(String, Vec<TermPattern>),
}

impl TermPattern {
    #[must_use]
    pub fn matches(&self, other: &Self, bindings: &mut BTreeMap<usize, TermPattern>) -> bool {
        match (self, other) {
            (Self::Wildcard(id), val) => {
                if let Some(existing) = bindings.get(id) {
                    existing == val
                } else {
                    bindings.insert(*id, val.clone());
                    true
                }
            }
            (Self::Const(c1), Self::Const(c2)) => c1 == c2,
            (Self::FloatBits(b1), Self::FloatBits(b2)) => b1 == b2,
            (Self::Var(v1), Self::Var(v2)) => v1 == v2,
            (Self::Compound(op1, ch1), Self::Compound(op2, ch2)) => {
                if op1 != op2 || ch1.len() != ch2.len() {
                    false
                } else {
                    ch1.iter()
                        .zip(ch2.iter())
                        .all(|(c1, c2)| c1.matches(c2, bindings))
                }
            }
            _ => false,
        }
    }

    #[must_use]
    pub fn substitute(&self, bindings: &BTreeMap<usize, TermPattern>) -> Self {
        match self {
            Self::Wildcard(id) => bindings.get(id).cloned().unwrap_or_else(|| self.clone()),
            Self::Compound(op, children) => {
                let subst_children = children.iter().map(|c| c.substitute(bindings)).collect();
                Self::Compound(op.clone(), subst_children)
            }
            other => other.clone(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SynthesizedMacroRule {
    pub rule_id: String,
    pub lhs_pattern: TermPattern,
    pub rhs_template: TermPattern,
    pub verification_proof_steps: usize,
    pub compression_ratio: f64,
}

impl SynthesizedMacroRule {
    #[must_use]
    pub fn apply_direct(&self, input: &TermPattern) -> Option<TermPattern> {
        let mut bindings = BTreeMap::new();
        if self.lhs_pattern.matches(input, &mut bindings) {
            Some(self.rhs_template.substitute(&bindings))
        } else {
            None
        }
    }
}

#[derive(Debug, Default)]
pub struct AntiUnificationEngine;

impl AntiUnificationEngine {
    #[must_use]
    pub fn synthesize_rule(
        rule_id: &str,
        lhs: TermPattern,
        rhs: TermPattern,
        original_steps: usize,
    ) -> SynthesizedMacroRule {
        let compression = if original_steps > 0 {
            original_steps as f64 / 1.0
        } else {
            1.0
        };
        SynthesizedMacroRule {
            rule_id: rule_id.to_string(),
            lhs_pattern: lhs,
            rhs_template: rhs,
            verification_proof_steps: original_steps,
            compression_ratio: compression,
        }
    }
}
