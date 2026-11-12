use serde::{Deserialize, Serialize};

use super::codec::{Cloud, ParticleError};
use super::sample::{Part, Spec, sample};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum LodLevel {
    BaseShell,
    InternalCore,
    FineDetails,
    FullUltra,
}

impl LodLevel {
    #[must_use]
    pub const fn point_budget(self) -> u32 {
        match self {
            Self::BaseShell => 2_500,
            Self::InternalCore => 6_000,
            Self::FineDetails => 12_000,
            Self::FullUltra => 24_000,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProgressiveAssembly {
    pub shell: Spec,
    pub core: Spec,
    pub fine: Spec,
    pub full: Spec,
}

#[must_use]
pub fn decompose_lod(spec: &Spec) -> ProgressiveAssembly {
    let total = spec.parts.len();
    if total <= 2 {
        return ProgressiveAssembly {
            shell: spec.clone(),
            core: spec.clone(),
            fine: spec.clone(),
            full: spec.clone(),
        };
    }

    let shell_count = 2.max(total.saturating_div(3));
    let core_count = shell_count
        .saturating_add(total.saturating_div(3))
        .min(total);

    let shell_parts: Vec<Part> = spec.parts.iter().take(shell_count).cloned().collect();
    let core_parts: Vec<Part> = spec.parts.iter().take(core_count).cloned().collect();

    ProgressiveAssembly {
        shell: Spec { parts: shell_parts },
        core: Spec { parts: core_parts },
        fine: spec.clone(),
        full: spec.clone(),
    }
}

pub fn sample_progressive_layer(
    spec: &Spec,
    level: LodLevel,
    seed: u64,
) -> Result<Cloud, ParticleError> {
    let assembly = decompose_lod(spec);
    let target_spec = match level {
        LodLevel::BaseShell => &assembly.shell,
        LodLevel::InternalCore => &assembly.core,
        LodLevel::FineDetails => &assembly.fine,
        LodLevel::FullUltra => &assembly.full,
    };
    sample(target_spec, level.point_budget(), seed)
}
