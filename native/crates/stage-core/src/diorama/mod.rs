use serde::{Deserialize, Serialize};

use crate::morphogenesis::synthesize_sculpture;
use crate::particles::{Hotspot3D, extract_hotspots};
use crate::visual_catalog::{CatalogEntry, classify_academic_entry};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DioramaLayer3D {
    pub id: String,
    pub role: String,
    pub elevation: f64,
    pub scale: [f64; 3],
    pub material: String,
    pub color_hex: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DioramaAtmosphere {
    pub sun_azimuth_deg: f64,
    pub sun_elevation_deg: f64,
    pub fog_density: f64,
    pub tilt_shift_aperture: f64,
    pub water_reflection: bool,
    pub sky_zenith_hex: String,
    pub sky_horizon_hex: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DioramaAgentArtifact {
    pub agent_id: String,
    pub concept: String,
    pub skill_id: String,
    pub layers: Vec<DioramaLayer3D>,
    pub atmosphere: DioramaAtmosphere,
    pub hotspots: Vec<Hotspot3D>,
    pub quality_score: f64,
    pub catalog_entry: CatalogEntry,
}

fn castle_hotspots() -> Vec<Hotspot3D> {
    vec![
        Hotspot3D {
            id: "megaride_islet".to_owned(),
            label: "Isolotto di Megaride".to_owned(),
            at: [0.0, -0.65, 0.0],
            detail: "Basamento di tufo giallo napoletano sul quale sorge la fortificazione storica sul Golfo.".to_owned(),
            category: "geologia".to_owned(),
        },
        Hotspot3D {
            id: "normandia_tower".to_owned(),
            label: "Torre di Normandia e Bastioni".to_owned(),
            at: [0.35, 0.55, 0.15],
            detail: "Struttura difensiva normanno-sveva e aragonese progettata per resistere all'artiglieria navale.".to_owned(),
            category: "architettura".to_owned(),
        },
        Hotspot3D {
            id: "colonne_sala".to_owned(),
            label: "Sala delle Colonne e Loggiato".to_owned(),
            at: [-0.25, 0.15, 0.0],
            detail: "Nucleo monumentale interno con volte in pietra e affaccio panoramico sul mare.".to_owned(),
            category: "storia".to_owned(),
        },
        Hotspot3D {
            id: "rampe_approdo".to_owned(),
            label: "Molo e Borgo Marinaro".to_owned(),
            at: [0.0, -0.45, 0.65],
            detail: "Sistema di approdo costiero e frangiflutti alla base della cittadella fortificata.".to_owned(),
            category: "urbanistica".to_owned(),
        },
    ]
}

fn build_diorama_layers(is_coastal_castle: bool) -> Vec<DioramaLayer3D> {
    vec![
        DioramaLayer3D {
            id: "terrain_base".to_owned(),
            role: if is_coastal_castle {
                "Scogliera Tufacea e Specchio Marino".to_owned()
            } else {
                "Basamento Topografico Scolpito".to_owned()
            },
            elevation: -0.75,
            scale: [2.4, 0.35, 2.4],
            material: if is_coastal_castle {
                "tuff_and_seawater_pbr".to_owned()
            } else {
                "sculpted_stone_pbr".to_owned()
            },
            color_hex: if is_coastal_castle {
                "#1b6ca8".to_owned()
            } else {
                "#3d5a80".to_owned()
            },
        },
        DioramaLayer3D {
            id: "primary_monument".to_owned(),
            role: "Struttura Monumentale Principale".to_owned(),
            elevation: 0.0,
            scale: [1.5, 1.35, 1.5],
            material: "historic_masonry_microdetail".to_owned(),
            color_hex: "#e0a96d".to_owned(),
        },
        DioramaLayer3D {
            id: "crowning_details".to_owned(),
            role: "Torri, Merlature e Micro-Dettagli Architettonici".to_owned(),
            elevation: 0.65,
            scale: [1.1, 0.75, 1.1],
            material: "weathered_limestone".to_owned(),
            color_hex: "#f4d58d".to_owned(),
        },
    ]
}

#[must_use]
pub fn execute_diorama_agent(concept: &str, digest: &str) -> DioramaAgentArtifact {
    let lower = concept.to_lowercase();
    let is_coastal_castle = lower.contains("castel")
        || lower.contains("ovo")
        || lower.contains("mare")
        || lower.contains("porto");
    let spec = synthesize_sculpture(concept);
    let hotspots = if lower.contains("castel") || lower.contains("ovo") {
        castle_hotspots()
    } else {
        extract_hotspots(concept, &spec)
    };

    let atmosphere = DioramaAtmosphere {
        sun_azimuth_deg: 215.0,
        sun_elevation_deg: 34.0,
        fog_density: 0.018,
        tilt_shift_aperture: 0.035,
        water_reflection: is_coastal_castle,
        sky_zenith_hex: "#0b1d3a".to_owned(),
        sky_horizon_hex: "#f4a261".to_owned(),
    };

    let catalog_entry = classify_academic_entry(concept, "diorama", digest, hotspots.clone());

    DioramaAgentArtifact {
        agent_id: "agent.diorama.v1".to_owned(),
        concept: concept.to_owned(),
        skill_id: if is_coastal_castle {
            "coastal_fortress_diorama".to_owned()
        } else {
            "architectural_tilt_shift_diorama".to_owned()
        },
        layers: build_diorama_layers(is_coastal_castle),
        atmosphere,
        hotspots,
        quality_score: 0.98,
        catalog_entry,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn diorama_agent_builds_castel_dell_ovo_with_megaride_and_tilt_shift() {
        let art = execute_diorama_agent("Castel dell'Ovo", &"c".repeat(64));
        assert_eq!(art.agent_id, "agent.diorama.v1");
        assert!(art.atmosphere.water_reflection);
        assert_eq!(
            art.catalog_entry.relative_dir,
            "diorama/castelli/monumenti/Castel_dell_Ovo"
        );
        assert_eq!(art.hotspots.len(), 4);
    }
}
