use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::error::ThoughtError;

pub const MAX_CONTRACTS: usize = 256;
const MAX_ID_LEN: usize = 80;
const MAX_SCHEMA_LEN: usize = 16_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContractKind {
    HttpEndpoint,
    DataModel,
    EventTopic,
    SecurityInvariant,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct InterfaceContract {
    pub id: String,
    pub kind: ContractKind,
    pub producer_role: String,
    pub consumer_roles: Vec<String>,
    pub version: u32,
    pub schema: String,
    pub invariants: Vec<String>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ContractRegistry {
    contracts: BTreeMap<String, InterfaceContract>,
}

impl ContractRegistry {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.contracts.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.contracts.is_empty()
    }

    pub fn publish(
        &mut self,
        mut contract: InterfaceContract,
    ) -> Result<InterfaceContract, ThoughtError> {
        let id = contract.id.trim().to_owned();
        if id.is_empty() || id.len() > MAX_ID_LEN {
            return Err(ThoughtError::InvalidIdentifier(contract.id));
        }
        if contract.schema.trim().is_empty() || contract.schema.len() > MAX_SCHEMA_LEN {
            return Err(ThoughtError::InvalidText {
                field: "schema",
                reason: "must be non-empty and within 16KB",
            });
        }
        if contract.producer_role.trim().is_empty() {
            return Err(ThoughtError::InvalidText {
                field: "producer_role",
                reason: "producer role is required",
            });
        }
        if !self.contracts.contains_key(&id) && self.contracts.len() >= MAX_CONTRACTS {
            return Err(ThoughtError::ContractConflict {
                id,
                reason: "maximum number of contracts reached".to_owned(),
            });
        }
        let next_version = self
            .contracts
            .get(&id)
            .map_or(1, |prev| prev.version.saturating_add(1));
        contract.id.clone_from(&id);
        contract.version = next_version;
        self.contracts.insert(id, contract.clone());
        Ok(contract)
    }

    #[must_use]
    pub fn get(&self, id: &str) -> Option<&InterfaceContract> {
        self.contracts.get(id.trim())
    }

    #[must_use]
    pub fn for_role(&self, role: &str) -> Vec<&InterfaceContract> {
        let clean_role = role.trim();
        self.contracts
            .values()
            .filter(|c| {
                c.producer_role == clean_role || c.consumer_roles.iter().any(|r| r == clean_role)
            })
            .collect()
    }

    #[must_use]
    pub fn list(&self) -> Vec<&InterfaceContract> {
        self.contracts.values().collect()
    }
}
