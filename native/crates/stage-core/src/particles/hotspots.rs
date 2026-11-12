use serde::{Deserialize, Serialize};

use super::sample::Spec;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Hotspot3D {
    pub id: String,
    pub label: String,
    pub at: [f64; 3],
    pub detail: String,
    pub category: String,
}

fn make_spot(id: &str, label: &str, at: [f64; 3], detail: &str, category: &str) -> Hotspot3D {
    Hotspot3D {
        id: id.to_owned(),
        label: label.to_owned(),
        at,
        detail: detail.to_owned(),
        category: category.to_owned(),
    }
}

#[must_use]
pub fn extract_hotspots(concept: &str, spec: &Spec) -> Vec<Hotspot3D> {
    let lower = concept.to_lowercase();
    let mut spots = Vec::with_capacity(6);

    if lower.contains("cervell") || lower.contains("brain") {
        spots.push(make_spot(
            "frontal_lobe",
            "Lobo Frontale",
            [0.0, 0.45, 0.35],
            "Pianificazione strategica, decisione e pensiero logico astratto.",
            "anatomia",
        ));
        spots.push(make_spot(
            "temporal_lobes",
            "Lobi Temporali",
            [-0.45, 0.1, 0.0],
            "Elaborazione del linguaggio, memoria semantica e riconoscimento uditivo.",
            "anatomia",
        ));
        spots.push(make_spot(
            "cerebellum",
            "Cervelletto",
            [0.0, -0.45, -0.45],
            "Coordinamento motorio fine, equilibrio e postura corporea.",
            "funzione",
        ));
        spots.push(make_spot(
            "brainstem",
            "Tronco Encefalico",
            [0.0, -0.75, -0.1],
            "Regolazione dei ritmi vitali involontari, respiro e battito cardiaco.",
            "fisiologia",
        ));
        return spots;
    }

    if lower.contains("medusa") || lower.contains("jellyfish") || lower.contains("cnidar") {
        spots.push(make_spot(
            "umbrella",
            "Esombrella",
            [0.0, 0.85, 0.0],
            "Cupola gelatinosa a contrazione idrodinamica pulsante per il nuoto.",
            "struttura",
        ));
        spots.push(make_spot(
            "subumbrella",
            "Anello Subombrellare",
            [0.0, 0.45, 0.0],
            "Fasci muscolari circolari che generano la spinta idraulica ritmica.",
            "motoria",
        ));
        spots.push(make_spot(
            "gastrovascular",
            "Cavità Gastrovascolare",
            [0.0, 0.15, 0.0],
            "Sistema digerente e distributivo dei nutrienti cellulari.",
            "nutrizione",
        ));
        spots.push(make_spot(
            "tentacles",
            "Tentacoli e Cnidociti",
            [0.6, -0.75, 0.0],
            "Filamenti urticanti per la difesa e la cattura di prede tramite microscopici arpioni.",
            "difesa",
        ));
        return spots;
    }

    if lower.contains("motore") || lower.contains("engine") || lower.contains("turbin") {
        spots.push(make_spot(
            "combustion",
            "Camera di Combustione",
            [0.0, 0.2, 0.0],
            "Zona di espansione termodinamica del fluido ad alta pressione.",
            "energia",
        ));
        spots.push(make_spot(
            "stator",
            "Stadio Rotorico",
            [-0.55, 0.0, 0.0],
            "Palette calettate per la conversione dell'energia cinetica in coppia motrice.",
            "meccanica",
        ));
        spots.push(make_spot(
            "exhaust",
            "Ugello di Scarico",
            [0.85, 0.0, 0.0],
            "Accelerazione supersonica dei gas combusti per la spinta propulsiva.",
            "fluidodinamica",
        ));
        return spots;
    }

    for (idx, part) in spec.parts.iter().take(4).enumerate() {
        let label = format!("Elemento {idx}");
        let id = format!("part_{idx}");
        spots.push(make_spot(
            &id,
            &label,
            part.at,
            "Componente strutturale tridimensionale della morfologia olografica.",
            "struttura",
        ));
    }
    spots
}
