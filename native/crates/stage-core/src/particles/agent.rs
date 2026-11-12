use serde::{Deserialize, Serialize};

use crate::morphogenesis::synthesize_sculpture;
use crate::particles::{Hotspot3D, Part, Shape, Spec, extract_hotspots, sample};
use crate::visual_catalog::{CatalogEntry, classify_academic_entry};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ParticleAgentSkill {
    pub id: String,
    pub domain: String,
    pub description: String,
    pub min_parts: usize,
    pub target_points: u32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ParticleCritiqueReport {
    pub passed: bool,
    pub quality_score: f64,
    pub part_count: usize,
    pub hotspot_count: usize,
    pub point_density: u32,
    pub refinements_applied: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParticleAgentArtifact {
    pub agent_id: String,
    pub concept: String,
    pub skill_used: ParticleAgentSkill,
    pub spec: Spec,
    pub critique: ParticleCritiqueReport,
    pub catalog_entry: CatalogEntry,
    pub point_count: u32,
}

#[must_use]
pub fn particle_agent_skills() -> Vec<ParticleAgentSkill> {
    vec![
        ParticleAgentSkill {
            id: "bioluminescent_marine_zoology".to_owned(),
            domain: "animali/mare".to_owned(),
            description: "Sintesi ad altissima densità di cnidari, cefalopodi e organismi abissali con stratificazione esombrellare e tentacolare.".to_owned(),
            min_parts: 10,
            target_points: 24_000,
        },
        ParticleAgentSkill {
            id: "neuro_cardiac_anatomy".to_owned(),
            domain: "anatomia/corpo_umano".to_owned(),
            description: "Ricostruzione volumetrica di lobi cerebrali, fasci muscolari, strutture vascolari ed eliche genomiche.".to_owned(),
            min_parts: 9,
            target_points: 24_000,
        },
        ParticleAgentSkill {
            id: "thermodynamic_propulsion".to_owned(),
            domain: "auto/motori".to_owned(),
            description: "Architettura meccanica di bancate cilindri, rotori, statori e camere di combustione.".to_owned(),
            min_parts: 10,
            target_points: 20_000,
        },
        ParticleAgentSkill {
            id: "astrophysics_quantum_lattice".to_owned(),
            domain: "astronomia/cosmo".to_owned(),
            description: "Sistemi orbitali, anelli planetari, reticoli cristallini e orbitali molecolari.".to_owned(),
            min_parts: 8,
            target_points: 20_000,
        },
    ]
}

fn select_skill(concept: &str) -> ParticleAgentSkill {
    let lower = concept.to_lowercase();
    let skills = particle_agent_skills();
    let idx = if [
        "medusa",
        "rhizostoma",
        "polp",
        "calamar",
        "squalo",
        "delfin",
        "balen",
        "pesce",
    ]
    .iter()
    .any(|k| lower.contains(k))
    {
        0
    } else if ["cervell", "cuore", "polmon", "neurone", "dna", "muscol"]
        .iter()
        .any(|k| lower.contains(k))
    {
        1
    } else if ["motore", "v8", "turbin", "auto", "aereo", "razzo"]
        .iter()
        .any(|k| lower.contains(k))
    {
        2
    } else {
        3
    };
    skills.into_iter().nth(idx).unwrap_or(ParticleAgentSkill {
        id: "universal_morphogenesis".to_owned(),
        domain: "enciclopedia/modelli".to_owned(),
        description: "Sintesi universale procedurale".to_owned(),
        min_parts: 8,
        target_points: 20_000,
    })
}

fn self_criticize_and_refine(
    concept: &str,
    mut spec: Spec,
    mut hotspots: Vec<Hotspot3D>,
    skill: &ParticleAgentSkill,
) -> (Spec, Vec<Hotspot3D>, ParticleCritiqueReport) {
    let mut refinements = Vec::new();

    if spec.parts.len() < skill.min_parts && spec.parts.len() < 22 {
        let missing = skill.min_parts.saturating_sub(spec.parts.len());
        let denom = f64::from(u32::try_from(missing.max(1)).unwrap_or(1));
        for idx in 0..missing {
            let num = f64::from(u32::try_from(idx).unwrap_or(0));
            let angle = (num / denom) * std::f64::consts::TAU;
            spec.parts.push(Part {
                shape: Shape::Helix,
                size: [0.16, 0.55, 0.16],
                at: [0.65 * angle.cos(), -0.35, 0.65 * angle.sin()],
                rot: [0.0, angle.to_degrees(), 0.0],
                color: "#5ef2ff".to_owned(),
                weight: 0.85,
            });
        }
        refinements.push(format!(
            "Aggiunti {missing} micro-filamenti strutturali di rifinitura"
        ));
    }

    if hotspots.len() < 4 {
        hotspots.push(Hotspot3D {
            id: "micro_cortex".to_owned(),
            label: format!("Struttura Fine di {concept}"),
            at: [0.0, 0.0, 0.35],
            detail: "Reticolo secondario ad alta densità generato dall'autocritica dell'Agente Particelle.".to_owned(),
            category: "microstruttura".to_owned(),
        });
        refinements.push("Arricchiti i punti di ispezione accademica".to_owned());
    }

    let part_len = f64::from(u32::try_from(spec.parts.len()).unwrap_or(12));
    let spot_len = f64::from(u32::try_from(hotspots.len()).unwrap_or(4));
    let score = ((part_len / 12.0).min(1.0) * 0.55) + ((spot_len / 4.0).min(1.0) * 0.45);

    let report = ParticleCritiqueReport {
        passed: score >= 0.75,
        quality_score: (score * 1000.0).round() / 1000.0,
        part_count: spec.parts.len(),
        hotspot_count: hotspots.len(),
        point_density: skill.target_points,
        refinements_applied: refinements,
    };

    (spec, hotspots, report)
}

#[must_use]
pub fn execute_particle_agent(concept: &str, digest: &str) -> ParticleAgentArtifact {
    let skill = select_skill(concept);
    let raw_spec = synthesize_sculpture(concept);
    let raw_spots = extract_hotspots(concept, &raw_spec);
    let (spec, hotspots, critique) =
        self_criticize_and_refine(concept, raw_spec, raw_spots, &skill);
    let _ = sample(&spec, 512, 42);
    let catalog_entry = classify_academic_entry(concept, "particles", digest, hotspots);

    ParticleAgentArtifact {
        agent_id: "agent.particles.v1".to_owned(),
        concept: concept.to_owned(),
        point_count: skill.target_points,
        skill_used: skill,
        spec,
        critique,
        catalog_entry,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn autonomous_particle_agent_plans_criticizes_and_refines_medusa() {
        let artifact = execute_particle_agent("medusa", &"a".repeat(64));
        assert_eq!(artifact.agent_id, "agent.particles.v1");
        assert!(artifact.critique.passed);
        assert!(artifact.spec.parts.len() >= 10);
        assert_eq!(
            artifact.catalog_entry.relative_dir,
            "particelle/animali/mare/Rhizostoma_pulmo"
        );
    }
}
