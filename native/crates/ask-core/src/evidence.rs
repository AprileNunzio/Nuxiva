use nuxiva_memory_core::{Class, EvidenceKind, Sighting, Who};
use serde::{Deserialize, Serialize};

use crate::matcher::ScoredMatch;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EvidenceCitation {
    pub sighting_id: String,
    pub timestamp_ms: u64,
    pub time_str: String,
    pub camera: String,
    #[serde(default)]
    pub zone: Option<String>,
    pub class: Class,
    pub who: Who,
    pub appearance_desc: String,
    #[serde(default)]
    pub frame_evidence_id: Option<String>,
    #[serde(default)]
    pub clip_evidence_id: Option<String>,
    pub confidence_pct: u8,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AskAnswer {
    pub found: bool,
    pub summary: String,
    pub citations: Vec<EvidenceCitation>,
    pub scanned: usize,
    pub matched_count: usize,
}

#[must_use]
pub fn format_time_hh_mm(ms: u64) -> String {
    let secs = ms / 1000;
    let day_secs = secs % 86_400;
    let hours = (day_secs / 3600) % 24;
    let mins = (day_secs % 3600) / 60;
    format!("{hours:02}:{mins:02}")
}

fn describe_appearance(s: &Sighting) -> String {
    let mut parts = Vec::new();
    if let Some(c) = s.look.upper {
        parts.push(format!("sopra {c:?}").to_lowercase());
    }
    if let Some(c) = s.look.lower {
        parts.push(format!("sotto {c:?}").to_lowercase());
    }
    if !s.look.carrying.is_empty() {
        let items: Vec<String> = s
            .look
            .carrying
            .iter()
            .map(|i| format!("{i:?}").to_lowercase())
            .collect();
        parts.push(items.join(", "));
    }
    if let Some(v) = &s.vehicle {
        if let Some(c) = v.color {
            parts.push(format!("{c:?} {:?}", v.kind).to_lowercase());
        } else {
            parts.push(format!("{:?}", v.kind).to_lowercase());
        }
    }
    if parts.is_empty() {
        "ordinario".to_owned()
    } else {
        parts.join(", ")
    }
}

impl EvidenceCitation {
    #[must_use]
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    pub fn from_sighting(s: &Sighting) -> Self {
        let mut frame_id = None;
        let mut clip_id = None;
        for ev in &s.evidence {
            match ev.kind {
                EvidenceKind::Frame => frame_id = Some(ev.id.clone()),
                EvidenceKind::Clip => clip_id = Some(ev.id.clone()),
                EvidenceKind::Audio => {}
            }
        }

        let conf = (s.confidence.clamp(0.0, 1.0) * 100.0).round();
        let confidence_pct = if conf >= 100.0 { 100 } else { conf as u8 };

        Self {
            sighting_id: s.id.clone(),
            timestamp_ms: s.start_ms,
            time_str: format_time_hh_mm(s.start_ms),
            camera: s.camera.clone(),
            zone: s.zone.clone(),
            class: s.class,
            who: s.who.clone(),
            appearance_desc: describe_appearance(s),
            frame_evidence_id: frame_id,
            clip_evidence_id: clip_id,
            confidence_pct,
        }
    }
}

#[must_use]
pub fn build_citations(matches: &[ScoredMatch<'_>], max_citations: usize) -> Vec<EvidenceCitation> {
    matches
        .iter()
        .take(max_citations)
        .map(|m| EvidenceCitation::from_sighting(m.sighting))
        .collect()
}
