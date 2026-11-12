use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::particles::Hotspot3D;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AcademicLectureCard {
    pub title: String,
    pub binomial_or_code: String,
    pub taxonomy_path: String,
    pub abstract_summary: String,
    pub structural_notes: String,
    pub hotspots: Vec<Hotspot3D>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CatalogEntry {
    pub engine_folder: String,
    pub domain: String,
    pub subdomain: String,
    pub slug: String,
    pub relative_dir: String,
    pub concept: String,
    pub digest: String,
    pub lecture: AcademicLectureCard,
}

#[derive(Debug, Default)]
pub struct CatalogIndex {
    by_concept: HashMap<String, CatalogEntry>,
    by_path: HashMap<String, String>,
}

fn sanitize_segment(raw: &str) -> String {
    let mut out = String::with_capacity(raw.len().min(48));
    let mut prev_underscore = false;
    for ch in raw.chars() {
        if ch.is_ascii_alphanumeric() {
            out.push(ch);
            prev_underscore = false;
        } else if (ch == ' ' || ch == '_' || ch == '-' || ch == '\'')
            && !out.is_empty()
            && !prev_underscore
        {
            out.push('_');
            prev_underscore = true;
        }
    }
    while out.ends_with('_') {
        out.pop();
    }
    if out.is_empty() {
        "oggetto".to_owned()
    } else {
        out
    }
}

#[must_use]
pub fn map_engine_folder(engine: &str) -> &'static str {
    match engine.trim().to_lowercase().as_str() {
        "diorama" | "scene_3d" => "diorama",
        "gaussian_splat" | "neural_radiance" | "depth_parallax" | "animazioni_3d" => {
            "animazioni_3d"
        }
        _ => "particelle",
    }
}

fn classify_living(
    lower: &str,
    concept: &str,
) -> Option<(&'static str, &'static str, String, String)> {
    if lower.contains("medusa")
        || lower.contains("rhizostoma")
        || lower.contains("cnidar")
        || lower.contains("jellyfish")
    {
        return Some((
            "animali",
            "mare",
            "Rhizostoma_pulmo".to_owned(),
            "Rhizostoma pulmo (Cnidaria · Scyphozoa)".to_owned(),
        ));
    }
    if [
        "polp", "octopus", "calamar", "squalo", "delfin", "balen", "pesce",
    ]
    .iter()
    .any(|k| lower.contains(k))
    {
        return Some((
            "animali",
            "mare",
            sanitize_segment(concept),
            "Fauna Marina Pelagica / Bentonica".to_owned(),
        ));
    }
    if [
        "aquila", "leone", "lupo", "orso", "cane", "gatto", "cavallo",
    ]
    .iter()
    .any(|k| lower.contains(k))
    {
        return Some((
            "animali",
            "terra",
            sanitize_segment(concept),
            "Vertebrata · Fauna Terrestre".to_owned(),
        ));
    }
    if ["cervell", "cuore", "polmon", "neurone", "dna", "cellula"]
        .iter()
        .any(|k| lower.contains(k))
    {
        return Some((
            "anatomia",
            "corpo_umano",
            sanitize_segment(concept),
            "Anatomia e Fisiologia Umana".to_owned(),
        ));
    }
    None
}

fn classify_engineered_or_cosmic(
    lower: &str,
    concept: &str,
) -> Option<(&'static str, &'static str, String, String)> {
    if ["motore", "v8", "turbina", "pistone", "cilindr"]
        .iter()
        .any(|k| lower.contains(k))
    {
        let slug = if lower.contains("v8") || lower.contains("motore") {
            "motore_v8".to_owned()
        } else {
            sanitize_segment(concept)
        };
        return Some((
            "auto",
            "motori",
            slug,
            "Propulsore Termodinamico Endotermico V8".to_owned(),
        ));
    }
    if ["auto", "telaio", "freno", "cambio", "sospension"]
        .iter()
        .any(|k| lower.contains(k))
    {
        return Some((
            "auto",
            "meccanica",
            sanitize_segment(concept),
            "Ingegneria dell'Autoveicolo".to_owned(),
        ));
    }
    if ["castel", "fortezza", "rocca"]
        .iter()
        .any(|k| lower.contains(k))
    {
        let slug = if lower.contains("ovo") {
            "Castel_dell_Ovo".to_owned()
        } else {
            sanitize_segment(concept)
        };
        return Some((
            "castelli",
            "monumenti",
            slug,
            "Architettura Fortificata Storica".to_owned(),
        ));
    }
    if [
        "pianeta",
        "saturno",
        "galassia",
        "stella",
        "buco nero",
        "sistema solare",
    ]
    .iter()
    .any(|k| lower.contains(k))
    {
        return Some((
            "astronomia",
            "cosmo",
            sanitize_segment(concept),
            "Astrofisica e Meccanica Celeste".to_owned(),
        ));
    }
    if ["atom", "molecol", "cristall", "quarzo"]
        .iter()
        .any(|k| lower.contains(k))
    {
        return Some((
            "scienza",
            "materia",
            sanitize_segment(concept),
            "Fisica della Materia e Cristallografia".to_owned(),
        ));
    }
    None
}

fn classify_domain_and_slug(concept: &str) -> (&'static str, &'static str, String, String) {
    let lower = concept.to_lowercase();
    if let Some(res) = classify_living(&lower, concept) {
        return res;
    }
    if let Some(res) = classify_engineered_or_cosmic(&lower, concept) {
        return res;
    }
    (
        "enciclopedia",
        "modelli",
        sanitize_segment(concept),
        "Tassonomia Strutturale Multidimensionale".to_owned(),
    )
}

#[must_use]
pub fn classify_academic_entry(
    concept: &str,
    engine: &str,
    digest: &str,
    hotspots: Vec<Hotspot3D>,
) -> CatalogEntry {
    let engine_folder = map_engine_folder(engine).to_owned();
    let (domain, subdomain, slug, binomial) = classify_domain_and_slug(concept);
    let relative_dir = format!("{engine_folder}/{domain}/{subdomain}/{slug}");
    let title = concept.trim();
    let display_title = if title.is_empty() {
        slug.replace('_', " ")
    } else {
        title.to_owned()
    };

    let abstract_summary = format!(
        "Analisi accademica tridimensionale di «{display_title}» ({binomial}). Ruota il modello con il cursore, usa lo zoom per ispezionare la micro-architettura e seleziona ciascun nodo anatomico o meccanico per la spiegazione cattedratica dettagliata."
    );
    let structural_notes = format!(
        "Archiviato in {relative_dir} · Motore: {engine_folder} · Punti di ispezione attivi: {}",
        hotspots.len()
    );

    CatalogEntry {
        engine_folder,
        domain: domain.to_owned(),
        subdomain: subdomain.to_owned(),
        slug,
        relative_dir: relative_dir.clone(),
        concept: concept.trim().to_lowercase(),
        digest: digest.to_owned(),
        lecture: AcademicLectureCard {
            title: display_title,
            binomial_or_code: binomial,
            taxonomy_path: relative_dir,
            abstract_summary,
            structural_notes,
            hotspots,
        },
    }
}

impl CatalogIndex {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn upsert(&mut self, entry: CatalogEntry) {
        let key = entry.concept.trim().to_lowercase();
        self.by_path.insert(entry.relative_dir.clone(), key.clone());
        self.by_concept.insert(key, entry);
    }

    #[must_use]
    pub fn get_by_concept(&self, concept: &str) -> Option<&CatalogEntry> {
        let key = concept.trim().to_lowercase();
        self.by_concept.get(&key)
    }

    #[must_use]
    pub fn get_by_path(&self, relative_dir: &str) -> Option<&CatalogEntry> {
        let key = self.by_path.get(relative_dir)?;
        self.by_concept.get(key)
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.by_concept.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.by_concept.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::morphogenesis::synthesize_sculpture;
    use crate::particles::extract_hotspots;

    #[test]
    fn organizes_medusa_motore_and_castel_dell_ovo_into_exact_hierarchy() {
        let medusa_spec = synthesize_sculpture("medusa");
        let medusa_spots = extract_hotspots("medusa", &medusa_spec);
        let medusa =
            classify_academic_entry("medusa", "particles", "a".repeat(64).as_str(), medusa_spots);
        assert_eq!(
            medusa.relative_dir,
            "particelle/animali/mare/Rhizostoma_pulmo"
        );
        assert!(medusa.lecture.binomial_or_code.contains("Rhizostoma pulmo"));

        let v8_spec = synthesize_sculpture("motore v8");
        let v8_spots = extract_hotspots("motore v8", &v8_spec);
        let v8 = classify_academic_entry(
            "motore v8",
            "gaussian_splat",
            "b".repeat(64).as_str(),
            v8_spots,
        );
        assert_eq!(v8.relative_dir, "animazioni_3d/auto/motori/motore_v8");

        let castello_spec = synthesize_sculpture("Castel dell'Ovo");
        let castello_spots = extract_hotspots("Castel dell'Ovo", &castello_spec);
        let castello = classify_academic_entry(
            "Castel dell'Ovo",
            "diorama",
            "c".repeat(64).as_str(),
            castello_spots,
        );
        assert_eq!(
            castello.relative_dir,
            "diorama/castelli/monumenti/Castel_dell_Ovo"
        );

        let mut index = CatalogIndex::new();
        index.upsert(medusa);
        index.upsert(v8);
        index.upsert(castello);
        assert_eq!(index.len(), 3);
        assert!(index.get_by_concept("medusa").is_some());
        assert!(
            index
                .get_by_path("particelle/animali/mare/Rhizostoma_pulmo")
                .is_some()
        );
    }
}
