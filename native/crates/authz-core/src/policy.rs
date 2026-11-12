use std::collections::BTreeMap;

use serde_json::Value;

use crate::levels::{Risk, Strength};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Verdict {
    Ok,
    Role,
    Proof,
}

impl Verdict {
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::Ok => "ok",
            Self::Role => "role",
            Self::Proof => "proof",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Decision {
    pub verdict: Verdict,
    pub risk: Risk,
    pub needed: Strength,
}

impl Decision {
    #[must_use]
    pub fn allowed(self) -> bool {
        self.verdict == Verdict::Ok
    }
}

#[derive(Debug, Clone)]
pub struct Policy {
    defaults_ceiling: BTreeMap<String, Risk>,
    defaults_proof: BTreeMap<Risk, Strength>,
    subroles: BTreeMap<String, Risk>,
    ceiling: BTreeMap<String, Risk>,
    proof: BTreeMap<Risk, Strength>,
}

impl Policy {
    #[must_use]
    pub fn new(
        ceiling: BTreeMap<String, Risk>,
        proof: BTreeMap<Risk, Strength>,
        subroles: BTreeMap<String, Risk>,
    ) -> Self {
        Self {
            defaults_ceiling: ceiling.clone(),
            defaults_proof: proof.clone(),
            subroles,
            ceiling,
            proof,
        }
    }

    pub fn apply(&mut self, data: &Value) {
        let mut ceiling = self.defaults_ceiling.clone();
        let mut proof = self.defaults_proof.clone();
        if let Some(rows) = data.get("ceiling").and_then(Value::as_object) {
            for (role, name) in rows {
                let risk = name.as_str().and_then(Risk::parse);
                if let (true, Some(risk)) = (ceiling.contains_key(role) && role != "system", risk) {
                    ceiling.insert(role.clone(), risk);
                }
            }
        }
        if let Some(rows) = data.get("proof").and_then(Value::as_object) {
            for (name, strength) in rows {
                let risk = Risk::parse(name);
                let text = match strength {
                    Value::String(s) => s.clone(),
                    other => other.to_string(),
                };
                let level = Strength::parse_upper(&text);
                if let (Some(risk), Some(level)) = (risk, level) {
                    if risk >= Risk::Personal {
                        let floor = if risk == Risk::Critical {
                            Strength::Strong
                        } else {
                            Strength::Weak
                        };
                        proof.insert(risk, level.max(floor));
                    }
                }
            }
        }
        self.ceiling = ceiling;
        self.proof = proof;
    }

    #[must_use]
    pub fn limit(&self, role: &str, subrole: &str, custom: &str) -> Risk {
        let base = match self.subroles.get(subrole) {
            Some(risk) if !subrole.is_empty() => *risk,
            _ => self
                .ceiling
                .get(role)
                .or_else(|| self.ceiling.get("anonymous"))
                .copied()
                .unwrap_or(Risk::Info),
        };
        match Risk::parse(custom) {
            Some(risk) if role != "system" => risk,
            _ => base,
        }
    }

    #[must_use]
    pub fn check(
        &self,
        role: &str,
        subrole: &str,
        custom: &str,
        strength: Strength,
        risk: Risk,
    ) -> Decision {
        let needed = self.proof.get(&risk).copied().unwrap_or(Strength::Strong);
        let verdict = if risk > self.limit(role, subrole, custom) {
            Verdict::Role
        } else if strength < needed {
            Verdict::Proof
        } else {
            Verdict::Ok
        };
        Decision {
            verdict,
            risk,
            needed,
        }
    }

    #[must_use]
    pub fn ceiling(&self) -> &BTreeMap<String, Risk> {
        &self.ceiling
    }

    #[must_use]
    pub fn proof(&self) -> &BTreeMap<Risk, Strength> {
        &self.proof
    }
}
