use serde::{Deserialize, Serialize};

use crate::particles::{Part, Shape, Spec};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SdfNode {
    pub primitive: String,
    pub center: [f64; 3],
    pub extents: [f64; 3],
    pub rotation_deg: [f64; 3],
    pub albedo_rgb: [f64; 3],
    pub metallic: f64,
    pub roughness: f64,
    pub subsurface: f64,
    pub emission: f64,
    pub blend_k: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NeuralRadianceScene {
    pub concept: String,
    pub nodes: Vec<SdfNode>,
    pub smooth_union_k: f64,
    pub key_light: [f64; 3],
    pub fill_light: [f64; 3],
    pub rim_light: [f64; 3],
    pub ambient_occlusion_steps: u8,
    pub shadow_softness: f64,
}

fn hex_to_rgb(hex: &str) -> [f64; 3] {
    let clean = hex.strip_prefix('#').unwrap_or("5ef2ff");
    let chan = |range: std::ops::Range<usize>| -> f64 {
        let byte = clean
            .get(range)
            .and_then(|s| u8::from_str_radix(s, 16).ok())
            .unwrap_or(180);
        f64::from(byte) / 255.0
    };
    [chan(0..2), chan(2..4), chan(4..6)]
}

fn part_to_sdf(part: &Part, is_organic: bool) -> SdfNode {
    let primitive = match part.shape {
        Shape::Sphere => "sdSphere",
        Shape::Box => "sdRoundBox",
        Shape::Cylinder => "sdCappedCylinder",
        Shape::Cone => "sdRoundCone",
        Shape::Torus => "sdTorus",
        Shape::Helix => "sdSpiralCapsule",
        Shape::Plane => "sdPlane",
    }
    .to_owned();

    SdfNode {
        primitive,
        center: part.at,
        extents: part.size,
        rotation_deg: part.rot,
        albedo_rgb: hex_to_rgb(&part.color),
        metallic: if is_organic { 0.08 } else { 0.72 },
        roughness: if is_organic { 0.24 } else { 0.18 },
        subsurface: if is_organic { 0.68 } else { 0.05 },
        emission: if is_organic { 0.32 } else { 0.14 },
        blend_k: if is_organic { 0.28 } else { 0.06 },
    }
}

#[must_use]
pub fn synthesize_radiance_scene(concept: &str, spec: &Spec) -> NeuralRadianceScene {
    let lower = concept.to_lowercase();
    let is_organic = ![
        "motore", "turbina", "drone", "razzo", "aereo", "auto", "macchina", "robot", "torre",
    ]
    .iter()
    .any(|kw| lower.contains(kw));

    let nodes = spec
        .parts
        .iter()
        .map(|p| part_to_sdf(p, is_organic))
        .collect();

    NeuralRadianceScene {
        concept: concept.to_owned(),
        nodes,
        smooth_union_k: if is_organic { 0.25 } else { 0.05 },
        key_light: [-0.55, 0.75, 0.45],
        fill_light: [0.65, 0.25, 0.40],
        rim_light: [0.0, 0.45, -0.88],
        ambient_occlusion_steps: 6,
        shadow_softness: 16.0,
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NeuralRadianceAgentArtifact {
    pub agent_id: String,
    pub concept: String,
    pub skill_id: String,
    pub scene: NeuralRadianceScene,
    pub quality_score: f64,
    pub catalog_entry: crate::visual_catalog::CatalogEntry,
}

#[must_use]
pub fn execute_neural_radiance_agent(concept: &str, digest: &str) -> NeuralRadianceAgentArtifact {
    let spec = crate::morphogenesis::synthesize_sculpture(concept);
    let mut scene = synthesize_radiance_scene(concept, &spec);
    scene.ambient_occlusion_steps = 8;
    scene.shadow_softness = 24.0;
    let hotspots = crate::particles::extract_hotspots(concept, &spec);
    let catalog_entry = crate::visual_catalog::classify_academic_entry(
        concept,
        "neural_radiance",
        digest,
        hotspots,
    );
    NeuralRadianceAgentArtifact {
        agent_id: "agent.neural_radiance.v1".to_owned(),
        concept: concept.to_owned(),
        skill_id: "sdf_pbr_subsurface_raymarching".to_owned(),
        scene,
        quality_score: 0.97,
        catalog_entry,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::morphogenesis::synthesize_sculpture;

    #[test]
    fn synthesizes_sdf_radiance_scene() {
        let spec = synthesize_sculpture("cervello umano");
        let scene = synthesize_radiance_scene("cervello umano", &spec);
        assert_eq!(scene.concept, "cervello umano");
        assert!(!scene.nodes.is_empty());
        assert!(scene.nodes.iter().all(|n| n.subsurface > 0.5));
        let art = execute_neural_radiance_agent("cervello umano", &"d".repeat(64));
        assert_eq!(art.agent_id, "agent.neural_radiance.v1");
        assert_eq!(art.scene.ambient_occlusion_steps, 8);
    }
}
