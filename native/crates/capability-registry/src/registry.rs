use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};

use crate::contract::Contract;
use crate::error::{RegistryError, RegistryResult};
use crate::search::Index;
use crate::types::{Effect, Origin, Role, State, ValueType};

pub const MAX_DOCUMENT_BYTES: usize = 8 * 1024 * 1024;
pub const MAX_CAPABILITIES: usize = 100_000;
pub const DOCUMENT_SCHEMA: u32 = 1;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Document {
    pub schema: u32,
    pub capabilities: Vec<Contract>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Hit {
    pub id: String,
    pub score: f64,
}

#[derive(Debug, Clone, Default)]
pub struct Registry {
    contracts: BTreeMap<String, Contract>,
    generation: u64,
    index: Index,
}

impl Registry {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn from_document(bytes: &[u8]) -> RegistryResult<Self> {
        if bytes.len() > MAX_DOCUMENT_BYTES {
            return Err(RegistryError::TooLarge);
        }
        let document: Document = serde_json::from_slice(bytes)?;
        if document.schema != DOCUMENT_SCHEMA || document.capabilities.len() > MAX_CAPABILITIES {
            return Err(RegistryError::Invalid("document"));
        }
        let mut registry = Self::new();
        for contract in document.capabilities {
            registry.insert(contract)?;
        }
        Ok(registry)
    }

    pub fn insert(&mut self, mut contract: Contract) -> RegistryResult<u64> {
        contract.validate()?;
        if self.contracts.len() >= MAX_CAPABILITIES {
            return Err(RegistryError::TooLarge);
        }
        if let Some(existing) = self.contracts.get(&contract.id) {
            if existing.origin != contract.origin || contract.version <= existing.version {
                return Err(RegistryError::Duplicate(contract.id));
            }
        }
        if !contract.origin.trusted() {
            contract.effects = Effect::all();
            contract.reversible = false;
            contract.state = State::Degraded;
        }
        self.contracts.insert(contract.id.clone(), contract);
        Ok(self.touch())
    }

    pub fn activate(&mut self, id: &str, effects: BTreeSet<Effect>) -> RegistryResult<u64> {
        let contract = self
            .contracts
            .get_mut(id)
            .ok_or_else(|| RegistryError::Unknown(id.to_owned()))?;
        if effects.is_empty() || contract.state == State::Revoked {
            return Err(RegistryError::Invalid("activation"));
        }
        contract.effects = effects;
        contract.state = State::Active;
        Ok(self.touch())
    }

    pub fn revoke(&mut self, id: &str) -> RegistryResult<u64> {
        let contract = self
            .contracts
            .get_mut(id)
            .ok_or_else(|| RegistryError::Unknown(id.to_owned()))?;
        contract.state = State::Revoked;
        Ok(self.touch())
    }

    fn touch(&mut self) -> u64 {
        self.generation = self.generation.saturating_add(1);
        self.index = Index::build(self.contracts.values());
        self.generation
    }

    #[must_use]
    pub fn generation(&self) -> u64 {
        self.generation
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.contracts.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.contracts.is_empty()
    }

    #[must_use]
    pub fn get(&self, id: &str) -> Option<&Contract> {
        self.contracts.get(id)
    }

    pub fn ids(&self) -> impl Iterator<Item = &str> {
        self.contracts.keys().map(String::as_str)
    }

    #[must_use]
    pub fn selectable(&self, role: Role) -> BTreeSet<&str> {
        self.contracts
            .values()
            .filter(|c| c.state == State::Active && role.permits(c.min_role))
            .map(|c| c.id.as_str())
            .collect()
    }

    #[must_use]
    pub fn retrieve(&self, query: &str, limit: usize, role: Role) -> Vec<Hit> {
        self.index
            .score(query, &self.selectable(role))
            .into_iter()
            .take(limit)
            .map(|(id, score)| Hit { id, score })
            .collect()
    }

    #[must_use]
    pub fn producers_of(&self, ty: ValueType, role: Role) -> Vec<&str> {
        self.selectable(role)
            .into_iter()
            .filter(|id| self.contracts.get(*id).is_some_and(|c| c.output == ty))
            .collect()
    }

    #[must_use]
    pub fn consumers_of(&self, ty: ValueType, role: Role) -> Vec<&str> {
        self.selectable(role)
            .into_iter()
            .filter(|id| {
                self.contracts
                    .get(*id)
                    .is_some_and(|c| c.inputs.iter().any(|p| p.ty == ty))
            })
            .collect()
    }

    #[must_use]
    pub fn untrusted(&self) -> Vec<&str> {
        self.contracts
            .values()
            .filter(|c| c.origin != Origin::Local)
            .map(|c| c.id.as_str())
            .collect()
    }
}
