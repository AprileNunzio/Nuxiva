mod procedural;
mod taxonomy;

use crate::particles::Spec;
use taxonomy::{MorphologyKind, classify_morphology};

const PREFIXES: &[&str] = &[
    "creami con delle particelle",
    "crea con delle particelle",
    "crea con le particelle",
    "mostrami con le particelle",
    "mostrami in particelle",
    "fammi vedere come e fatta",
    "fammi vedere come è fatta",
    "fammi vedere come e fatto",
    "fammi vedere come è fatto",
    "mi dici come e fatta",
    "mi dici come è fatta",
    "mi dici come e fatto",
    "mi dici come è fatto",
    "mi spieghi come e fatta",
    "mi spieghi come è fatta",
    "mi spieghi come e fatto",
    "mi spieghi come è fatto",
    "spiegami come e fatta",
    "spiegami come è fatta",
    "spiegami come e fatto",
    "spiegami come è fatto",
    "come sono fatte",
    "come sono fatti",
    "come e strutturata",
    "come è strutturata",
    "come e strutturato",
    "come è strutturato",
    "com e strutturata",
    "com è strutturata",
    "com e strutturato",
    "com è strutturato",
    "com'e strutturata",
    "com'è strutturata",
    "com'e strutturato",
    "com'è strutturato",
    "com e composta",
    "com è composta",
    "com e composto",
    "com è composto",
    "come e composta",
    "come è composta",
    "come e composto",
    "come è composto",
    "come e fatta",
    "come è fatta",
    "come e fatto",
    "come è fatto",
    "com e fatta",
    "com è fatta",
    "com e fatto",
    "com è fatto",
    "com'e fatta",
    "com'è fatta",
    "com'e fatto",
    "com'è fatto",
    "come funziona",
    "anatomia di",
    "struttura di",
    "forma di",
    "mostrami",
    "mi mostri",
    "mi mostra",
    "mi fai vedere",
    "puoi mostrarmi",
    "potresti mostrarmi",
    "mostrarmi",
    "fammi vedere",
    "visualizza",
    "ologramma di",
    "particelle di",
    "how is made",
    "how is a",
    "structure of",
    "anatomy of",
    "show me",
];

const ARTICLES: &[&str] = &[
    "un'", "uno", "una", "un", "il", "lo", "la", "i", "gli", "le", "l'", "del", "dello", "della",
    "dei", "degli", "delle", "di", "da", "in", "con", "per", "the", "an", "a", "of",
];

const STOP_TAILS: &[&str] = &[
    "con delle particelle",
    "con le particelle",
    "in particelle",
    "in 3d",
    "nel dettaglio",
    "esattamente",
    "per favore",
    "grazie",
    "made",
    "built",
    "structured",
];

fn clean_text(raw: &str) -> String {
    let mut out = String::with_capacity(raw.len());
    for ch in raw.chars() {
        let lower = ch.to_lowercase().next().unwrap_or(ch);
        if lower.is_alphanumeric() || lower == '\'' || lower == '’' || lower == '-' {
            out.push(if lower == '’' { '\'' } else { lower });
        } else {
            out.push(' ');
        }
    }
    out.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn strip_articles(input: &str) -> String {
    let mut words: Vec<&str> = input.split_whitespace().collect();
    while let Some(first) = words.first().copied() {
        if let Some(rest) = first
            .strip_prefix("l'")
            .or_else(|| first.strip_prefix("un'"))
        {
            if rest.is_empty() {
                words.remove(0);
            } else if let Some(slot) = words.first_mut() {
                *slot = rest;
            }
            break;
        }
        if ARTICLES.contains(&first) {
            words.remove(0);
        } else {
            break;
        }
    }
    words.into_iter().take(4).collect::<Vec<_>>().join(" ")
}

#[must_use]
pub fn extract_visual_concept(query: &str) -> Option<String> {
    let cleaned = clean_text(query);
    if cleaned.len() < 4 {
        return None;
    }
    let mut matched_tail: Option<&str> = None;
    for prefix in PREFIXES {
        if let Some(idx) = cleaned.find(prefix) {
            let after_idx = idx.saturating_add(prefix.len());
            if let Some(tail) = cleaned.get(after_idx..) {
                let trimmed = tail.trim();
                if !trimmed.is_empty() {
                    matched_tail = Some(trimmed);
                    break;
                }
            }
        }
    }
    let mut candidate = matched_tail?.to_owned();
    for tail in STOP_TAILS {
        if let Some(stripped) = candidate.strip_suffix(tail) {
            candidate = stripped.trim().to_owned();
        }
    }
    let subject = strip_articles(&candidate);
    if subject.len() >= 2 {
        Some(subject)
    } else {
        None
    }
}

#[must_use]
pub fn synthesize_sculpture(concept: &str) -> Spec {
    let lower = clean_text(concept);
    let desc = classify_morphology(&lower);
    match desc.kind {
        MorphologyKind::RadialOrganism | MorphologyKind::RadialMechanical => {
            procedural::generate_radial(desc)
        }
        MorphologyKind::BilateralOrganism | MorphologyKind::BilateralVehicle => {
            procedural::generate_bilateral(desc)
        }
        MorphologyKind::OrbitalSystem => procedural::generate_orbital(desc),
        MorphologyKind::HelicalSpiral => procedural::generate_helical(desc),
        MorphologyKind::BranchingNetwork => procedural::generate_branching(desc),
        MorphologyKind::AxialColumn => procedural::generate_axial(desc),
        MorphologyKind::PolyhedralLattice => procedural::generate_polyhedral(desc),
        MorphologyKind::HarmonicMultibody => procedural::generate_harmonic(desc),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::particles::sample;

    #[test]
    fn extracts_the_concept_from_polite_requests() {
        for text in [
            "Mi mostri una medusa?",
            "Mi mostra una medusa",
            "Mi fai vedere una medusa",
            "Puoi mostrarmi una medusa?",
        ] {
            assert_eq!(
                extract_visual_concept(text).as_deref(),
                Some("medusa"),
                "{text}"
            );
        }
    }

    #[test]
    fn extracts_medusa_and_synthesizes_valid_12k_cloud() {
        let concept = extract_visual_concept("Come è fatta una medusa?");
        assert_eq!(concept.as_deref(), Some("medusa"));
        let spec = synthesize_sculpture("medusa");
        assert!(spec.parts.len() >= 7);
        let cloud = sample(&spec, 12_000, 42);
        assert!(cloud.is_ok());
        assert_eq!(cloud.map_or(0, |c| c.len()), 12_000);
    }

    #[test]
    fn synthesizes_diverse_taxonomic_forms_procedurally() {
        for word in [
            "medusa",
            "aquila reale",
            "turbina idraulica",
            "drone supersonico",
            "atomo di idrogeno",
            "doppia elica del dna",
            "albero di quercia",
            "razzo spaziale",
            "cristallo di quarzo",
            "qualsiasi oggetto sconosciuto",
        ] {
            let spec = synthesize_sculpture(word);
            let cloud = sample(&spec, 4_000, 19);
            assert!(cloud.is_ok());
        }
    }
}
