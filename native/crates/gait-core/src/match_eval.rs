use serde::{Deserialize, Serialize};

use crate::signature::GaitSignature;

pub const SIMILARITY_THRESHOLD: f32 = 0.70;
pub const MIN_CONFIDENCE_THRESHOLD: f32 = 0.40;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GaitMatch {
    pub similarity: f32,
    pub confidence: f32,
    pub probable_match: bool,
    pub is_biometric_conclusive: bool,
    pub reference_id: Option<String>,
    pub reference_timestamp_ms: Option<u64>,
    pub narrative_it: String,
    pub narrative_en: String,
    pub narrative_fr: String,
    pub narrative_es: String,
}

#[must_use]
pub fn format_time_hh_mm(ts_ms: u64) -> String {
    let secs = ts_ms / 1000;
    let mins = (secs / 60) % 60;
    let hours = (secs / 3600) % 24;
    format!("{hours:02}:{mins:02}")
}

#[must_use]
pub fn format_day_month_it(ts_ms: u64) -> String {
    let days = ts_ms / 86_400_000;
    let day = (days % 31).saturating_add(1);
    let month_idx = (days / 31) % 12;
    let months = [
        "gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic",
    ];
    let m = months.get(month_idx as usize).copied().unwrap_or("nov");
    format!("{day} {m}")
}

#[must_use]
pub fn format_day_month_en(ts_ms: u64) -> String {
    let days = ts_ms / 86_400_000;
    let day = (days % 31).saturating_add(1);
    let month_idx = (days / 31) % 12;
    let months = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ];
    let m = months.get(month_idx as usize).copied().unwrap_or("Nov");
    format!("{m} {day}")
}

#[must_use]
#[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
pub fn evaluate_match(
    candidate: &GaitSignature,
    reference: &GaitSignature,
    ref_id: Option<&str>,
    ref_ts_ms: Option<u64>,
) -> GaitMatch {
    let cos_sim = candidate.cosine_similarity(reference);
    let weight_sim = candidate.weighted_similarity(reference);
    let similarity = (cos_sim * 0.5 + weight_sim * 0.5).clamp(0.0, 1.0);
    let base_conf = (candidate.confidence * reference.confidence).sqrt();
    let confidence = (base_conf * similarity).clamp(0.0, 1.0);
    let probable_match =
        similarity >= SIMILARITY_THRESHOLD && confidence >= MIN_CONFIDENCE_THRESHOLD;
    let conf_pct = (confidence * 100.0).round() as u32;
    let (time_str, date_it, date_en) = ref_ts_ms.map_or_else(
        || {
            (
                "--:--".to_owned(),
                "precedente".to_owned(),
                "previous".to_owned(),
            )
        },
        |ts| {
            (
                format_time_hh_mm(ts),
                format_day_month_it(ts),
                format_day_month_en(ts),
            )
        },
    );
    let (narr_it, narr_en, narr_fr, narr_es) = if probable_match {
        (
            format!(
                "probabilmente la stessa persona del {date_it} alle {time_str}, confidenza {conf_pct}%"
            ),
            format!("likely the same person from {date_en} at {time_str}, confidence {conf_pct}%"),
            format!(
                "probablement la même personne du {date_it} à {time_str}, confiance {conf_pct}%"
            ),
            format!(
                "probablemente la misma persona del {date_it} a las {time_str}, confianza {conf_pct}%"
            ),
        )
    } else {
        (
            format!("andatura non corrispondente, similarità {conf_pct}%"),
            format!("gait does not match, similarity {conf_pct}%"),
            format!("démarche non correspondante, similarité {conf_pct}%"),
            format!("marcha no coincidente, similitud {conf_pct}%"),
        )
    };
    GaitMatch {
        similarity,
        confidence,
        probable_match,
        is_biometric_conclusive: false,
        reference_id: ref_id.map(ToOwned::to_owned),
        reference_timestamp_ms: ref_ts_ms,
        narrative_it: narr_it,
        narrative_en: narr_en,
        narrative_fr: narr_fr,
        narrative_es: narr_es,
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ReferenceGait {
    pub id: String,
    pub timestamp_ms: u64,
    pub signature: GaitSignature,
}

#[must_use]
pub fn find_best_match(
    candidate: &GaitSignature,
    references: &[ReferenceGait],
) -> Option<GaitMatch> {
    if references.is_empty() {
        return None;
    }
    let mut best_match: Option<GaitMatch> = None;
    for r in references {
        let m = evaluate_match(candidate, &r.signature, Some(&r.id), Some(r.timestamp_ms));
        if let Some(prev) = &best_match {
            if m.similarity > prev.similarity {
                best_match = Some(m);
            }
        } else {
            best_match = Some(m);
        }
    }
    best_match
}
