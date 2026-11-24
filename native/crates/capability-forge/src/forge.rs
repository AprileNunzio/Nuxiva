use std::collections::{BTreeMap, BTreeSet};

use capability_registry::{Contract, Effect, Origin, Registry, Role};

use crate::error::{ForgeError, ForgeResult};
use crate::sandbox::{Artifact, Probe, Sandbox};

pub const MAX_CANDIDATES: usize = 256;
pub const MAX_ARTIFACT_BYTES: usize = 1024 * 1024;
pub const MIN_PROBES: usize = 3;
pub const MAX_PROBES: usize = 16;
pub const MAX_RUN_MILLIS: u32 = 5_000;
pub const SHADOW_STREAK: u8 = 5;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Stage {
    Drafted,
    Verified,
    Shadowed,
    Active,
    Quarantined,
}

#[derive(Debug, Clone)]
struct Candidate {
    stage: Stage,
    artifact: Artifact,
    probes: Vec<Probe>,
    effects: BTreeSet<Effect>,
    version: u32,
    streak: u8,
}

#[derive(Debug, Default)]
pub struct Forge {
    candidates: BTreeMap<String, Candidate>,
}

impl Forge {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    #[must_use]
    pub fn stage(&self, id: &str) -> Option<Stage> {
        self.candidates.get(id).map(|c| c.stage)
    }

    pub fn submit(
        &mut self,
        registry: &mut Registry,
        mut contract: Contract,
        artifact: Artifact,
        probes: Vec<Probe>,
    ) -> ForgeResult<()> {
        if artifact.size == 0 || artifact.size > MAX_ARTIFACT_BYTES || artifact.digest.is_empty() {
            return Err(ForgeError::Invalid("artifact"));
        }
        if !(MIN_PROBES..=MAX_PROBES).contains(&probes.len()) {
            return Err(ForgeError::Invalid("probes"));
        }
        if contract.effects.is_empty() {
            return Err(ForgeError::Invalid("effects"));
        }
        if self.candidates.len() >= MAX_CANDIDATES && !self.candidates.contains_key(&contract.id) {
            return Err(ForgeError::TooMany);
        }
        if self.stage(&contract.id) == Some(Stage::Quarantined) {
            return Err(ForgeError::Quarantined(contract.id));
        }
        contract.origin = Origin::Generated;
        let effects = contract.effects.clone();
        let id = contract.id.clone();
        let version = contract.version;
        registry.insert(contract)?;
        self.candidates.insert(
            id,
            Candidate {
                stage: Stage::Drafted,
                artifact,
                probes,
                effects,
                version,
                streak: 0,
            },
        );
        Ok(())
    }

    pub fn verify<S: Sandbox>(
        &mut self,
        registry: &mut Registry,
        id: &str,
        sandbox: &mut S,
    ) -> ForgeResult<Stage> {
        let candidate = self
            .candidates
            .get_mut(id)
            .ok_or_else(|| ForgeError::Unknown(id.to_owned()))?;
        match candidate.stage {
            Stage::Drafted => {}
            Stage::Quarantined => return Err(ForgeError::Quarantined(id.to_owned())),
            _ => return Err(ForgeError::WrongStage(id.to_owned())),
        }
        let mut passed = true;
        for probe in &candidate.probes {
            let Ok(seen) = sandbox.run(&candidate.artifact, &probe.input) else {
                passed = false;
                continue;
            };
            if !seen.effects.is_subset(&candidate.effects) {
                candidate.stage = Stage::Quarantined;
                registry.revoke(id)?;
                return Ok(Stage::Quarantined);
            }
            if seen.millis > MAX_RUN_MILLIS || !probe.expect.holds(&seen.output) {
                passed = false;
            }
        }
        if passed {
            candidate.stage = Stage::Verified;
        }
        Ok(candidate.stage)
    }

    pub fn shadow(&mut self, id: &str, agreed: bool) -> ForgeResult<Stage> {
        let candidate = self
            .candidates
            .get_mut(id)
            .ok_or_else(|| ForgeError::Unknown(id.to_owned()))?;
        match candidate.stage {
            Stage::Verified | Stage::Shadowed => {}
            Stage::Quarantined => return Err(ForgeError::Quarantined(id.to_owned())),
            _ => return Err(ForgeError::WrongStage(id.to_owned())),
        }
        if agreed {
            candidate.streak = candidate.streak.saturating_add(1);
            if candidate.streak >= SHADOW_STREAK {
                candidate.stage = Stage::Shadowed;
            }
        } else {
            candidate.streak = 0;
            candidate.stage = Stage::Verified;
        }
        Ok(candidate.stage)
    }

    pub fn activate(
        &mut self,
        registry: &mut Registry,
        id: &str,
        approver: Role,
    ) -> ForgeResult<u64> {
        let candidate = self
            .candidates
            .get_mut(id)
            .ok_or_else(|| ForgeError::Unknown(id.to_owned()))?;
        if candidate.stage != Stage::Shadowed {
            return Err(ForgeError::WrongStage(id.to_owned()));
        }
        let needed = if candidate.effects.iter().any(|e| e.irreversible_risk()) {
            Role::Owner
        } else {
            Role::Family
        };
        if !approver.permits(needed) {
            return Err(ForgeError::ApprovalTooLow);
        }
        let generation = registry.activate(id, candidate.effects.clone())?;
        candidate.stage = Stage::Active;
        Ok(generation)
    }

    pub fn retire(&mut self, registry: &mut Registry, id: &str) -> ForgeResult<()> {
        if !self.candidates.contains_key(id) {
            return Err(ForgeError::Unknown(id.to_owned()));
        }
        registry.revoke(id)?;
        self.candidates.remove(id);
        Ok(())
    }

    #[must_use]
    pub fn next_version(&self, id: &str) -> u32 {
        self.candidates
            .get(id)
            .map_or(1, |c| c.version.saturating_add(1))
    }
}
