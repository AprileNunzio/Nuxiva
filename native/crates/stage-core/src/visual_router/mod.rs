use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum VisualEngineKind {
    Particles,
    GaussianSplat,
    NeuralRadiance,
    DepthParallax,
    Diorama,
}

impl VisualEngineKind {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Particles => "particles",
            Self::GaussianSplat => "gaussian_splat",
            Self::NeuralRadiance => "neural_radiance",
            Self::DepthParallax => "depth_parallax",
            Self::Diorama => "diorama",
        }
    }

    #[must_use]
    pub const fn memory_mb_estimate(self) -> u32 {
        match self {
            Self::Particles => 4,
            Self::DepthParallax => 16,
            Self::Diorama => 32,
            Self::GaussianSplat => 64,
            Self::NeuralRadiance => 96,
        }
    }

    #[must_use]
    pub fn from_name(name: &str) -> Option<Self> {
        match name.trim().to_lowercase().as_str() {
            "particles" | "particelle" => Some(Self::Particles),
            "gaussian_splat" | "gaussian" | "3dgs" | "splat" => Some(Self::GaussianSplat),
            "neural_radiance" | "nerf" | "sdf" | "raymarching" | "realistic" => {
                Some(Self::NeuralRadiance)
            }
            "depth_parallax" | "depth" | "parallax" | "image_3d" | "png_3d" => {
                Some(Self::DepthParallax)
            }
            "diorama" | "scene_3d" => Some(Self::Diorama),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct VisualRouteDecision {
    pub selected_engine: VisualEngineKind,
    pub reason: String,
    pub explicit_override: bool,
    pub memory_budget_mb: u32,
    pub fallback_order: Vec<VisualEngineKind>,
}

fn detect_explicit_engine(query: &str) -> Option<VisualEngineKind> {
    let lower = query.to_lowercase();
    if ["gaussian", "splatting", "splat", "nuvola gaussiana", "3dgs"]
        .iter()
        .any(|kw| lower.contains(kw))
    {
        return Some(VisualEngineKind::GaussianSplat);
    }
    if [
        "nerf",
        "raymarching",
        "radiance",
        "sdf",
        "fotorealistico",
        "3d realistico",
        "luci e ombre",
        "effetto wow",
    ]
    .iter()
    .any(|kw| lower.contains(kw))
    {
        return Some(VisualEngineKind::NeuralRadiance);
    }
    if [
        "immagine 3d",
        "foto 3d",
        "png 3d",
        "rilievo 3d",
        "parallasse",
        "depth map",
        "da immagine",
    ]
    .iter()
    .any(|kw| lower.contains(kw))
    {
        return Some(VisualEngineKind::DepthParallax);
    }
    if ["diorama", "plastico 3d", "scena tilt-shift"]
        .iter()
        .any(|kw| lower.contains(kw))
    {
        return Some(VisualEngineKind::Diorama);
    }
    if ["con le particelle", "con delle particelle", "in particelle"]
        .iter()
        .any(|kw| lower.contains(kw))
    {
        return Some(VisualEngineKind::Particles);
    }
    None
}

#[must_use]
pub fn select_visual_engine(
    query: &str,
    brain_priority_csv: &str,
    available_memory_mb: u32,
) -> VisualRouteDecision {
    let mut priority: Vec<VisualEngineKind> = brain_priority_csv
        .split(',')
        .filter_map(VisualEngineKind::from_name)
        .collect();

    if priority.is_empty() {
        priority = vec![
            VisualEngineKind::Particles,
            VisualEngineKind::DepthParallax,
            VisualEngineKind::GaussianSplat,
            VisualEngineKind::NeuralRadiance,
            VisualEngineKind::Diorama,
        ];
    }

    if let Some(explicit) = detect_explicit_engine(query) {
        return VisualRouteDecision {
            selected_engine: explicit,
            reason: format!(
                "Richiesta esplicita dell'utente per il motore {}",
                explicit.as_str()
            ),
            explicit_override: true,
            memory_budget_mb: explicit.memory_mb_estimate(),
            fallback_order: priority,
        };
    }

    let budget = available_memory_mb.max(4);
    for candidate in &priority {
        if candidate.memory_mb_estimate() <= budget {
            return VisualRouteDecision {
                selected_engine: *candidate,
                reason: format!(
                    "Selezionato da priorità del Cervello ({}) entro budget {} MB",
                    candidate.as_str(),
                    budget
                ),
                explicit_override: false,
                memory_budget_mb: candidate.memory_mb_estimate(),
                fallback_order: priority,
            };
        }
    }

    VisualRouteDecision {
        selected_engine: VisualEngineKind::Particles,
        reason: "Fallback automatico a particelle (consumo minimo di memoria e massima velocità)"
            .to_owned(),
        explicit_override: false,
        memory_budget_mb: VisualEngineKind::Particles.memory_mb_estimate(),
        fallback_order: priority,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_to_particles_for_speed_and_low_memory() {
        let dec = select_visual_engine("Come è fatta una medusa?", "", 512);
        assert_eq!(dec.selected_engine, VisualEngineKind::Particles);
        assert!(!dec.explicit_override);
        assert_eq!(dec.memory_budget_mb, 4);
    }

    #[test]
    fn respects_explicit_request_or_brain_priority() {
        let explicit = select_visual_engine(
            "Mostrami una medusa in 3d realistico con luci e ombre",
            "particles,gaussian_splat",
            512,
        );
        assert_eq!(explicit.selected_engine, VisualEngineKind::NeuralRadiance);
        assert!(explicit.explicit_override);

        let prio =
            select_visual_engine("Come è fatta una medusa?", "gaussian_splat,particles", 512);
        assert_eq!(prio.selected_engine, VisualEngineKind::GaussianSplat);
        assert!(!prio.explicit_override);
    }
}
