use serde::{Deserialize, Serialize};

use crate::segment::Segment;

pub const MAX_MARKERS: usize = 20_000;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Span {
    pub start_ms: u64,
    pub end_ms: u64,
    pub segments: u32,
    pub audio: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Marker {
    pub at_ms: u64,
    pub camera: String,
    pub kind: String,
    pub id: String,
    pub label: String,
    #[serde(default)]
    pub score: f32,
}

#[must_use]
pub fn spans(segments: &[Segment], tolerance_ms: u64) -> Vec<Span> {
    let mut ordered: Vec<&Segment> = segments.iter().collect();
    ordered.sort_by_key(|s| s.start_ms);
    let mut out: Vec<Span> = Vec::new();
    for segment in ordered {
        if let Some(last) = out.last_mut() {
            if segment.start_ms <= last.end_ms.saturating_add(tolerance_ms) {
                last.end_ms = last.end_ms.max(segment.end_ms());
                last.segments = last.segments.saturating_add(1);
                last.audio = last.audio || segment.audio;
                continue;
            }
        }
        out.push(Span {
            start_ms: segment.start_ms,
            end_ms: segment.end_ms(),
            segments: 1,
            audio: segment.audio,
        });
    }
    out
}

#[must_use]
pub fn next_marker<'a>(
    markers: &'a [Marker],
    at_ms: u64,
    forward: bool,
    kinds: &[String],
) -> Option<&'a Marker> {
    let wanted = |m: &&Marker| kinds.is_empty() || kinds.contains(&m.kind);
    if forward {
        markers
            .iter()
            .filter(wanted)
            .filter(|m| m.at_ms > at_ms)
            .min_by_key(|m| (m.at_ms, m.id.clone()))
    } else {
        markers
            .iter()
            .filter(wanted)
            .filter(|m| m.at_ms < at_ms)
            .max_by_key(|m| (m.at_ms, m.id.clone()))
    }
}
