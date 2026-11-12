#![allow(clippy::cast_precision_loss, clippy::arithmetic_side_effects)]

use std::collections::BTreeMap;

use nuxiva_ear_core::vote::vote;
use serde::{Deserialize, Serialize};

use crate::error::{NvrError, NvrResult};

pub const MAX_UTTERANCES: usize = 20_000;
pub const MAX_TEXT: usize = 4000;
const UNKNOWN_WEIGHT: f32 = 0.5;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Utterance {
    pub source: String,
    pub start_ms: u64,
    pub end_ms: u64,
    pub text: String,
    #[serde(default)]
    pub speaker: Option<String>,
    #[serde(default)]
    pub speaker_score: f32,
    pub weight: f32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Turn {
    pub start_ms: u64,
    pub end_ms: u64,
    pub text: String,
    pub speaker: Option<String>,
    pub speaker_score: f32,
    pub agreement: f32,
    pub changed: usize,
    pub sources: Vec<String>,
}

fn overlap_ratio(a: (u64, u64), b: (u64, u64)) -> f32 {
    let inter = a.1.min(b.1).saturating_sub(a.0.max(b.0));
    let shorter = a.1.saturating_sub(a.0).min(b.1.saturating_sub(b.0)).max(1);
    inter as f32 / shorter as f32
}

fn clean_weight(w: f32) -> f32 {
    if w.is_finite() {
        w.clamp(0.0, 10.0)
    } else {
        0.0
    }
}

fn pick_speaker(group: &[&Utterance]) -> (Option<String>, f32) {
    let mut tally: BTreeMap<String, (f32, f32)> = BTreeMap::new();
    for u in group {
        let key = u.speaker.clone().unwrap_or_default();
        let score = if u.speaker_score.is_finite() {
            u.speaker_score.clamp(0.0, 1.0)
        } else {
            0.0
        };
        let gain = if key.is_empty() {
            UNKNOWN_WEIGHT
        } else {
            score
        };
        let entry = tally.entry(key).or_insert((0.0, 0.0));
        entry.0 += clean_weight(u.weight) * gain;
        entry.1 = entry.1.max(score);
    }
    let mut best: Option<(&String, (f32, f32))> = None;
    for (key, value) in &tally {
        if best.is_none_or(|(_, b)| value.0 > b.0) {
            best = Some((key, *value));
        }
    }
    match best {
        Some((key, (_, score))) if !key.is_empty() => (Some(key.clone()), score),
        _ => (None, 0.0),
    }
}

pub fn fuse(utterances: &[Utterance], min_overlap: f32) -> NvrResult<Vec<Turn>> {
    if utterances.len() > MAX_UTTERANCES || utterances.iter().any(|u| u.text.len() > MAX_TEXT) {
        return Err(NvrError::TooMany);
    }
    let mut ordered: Vec<&Utterance> = utterances
        .iter()
        .filter(|u| u.end_ms > u.start_ms && !u.text.trim().is_empty())
        .collect();
    ordered
        .sort_by(|a, b| (a.start_ms, a.end_ms, &a.source).cmp(&(b.start_ms, b.end_ms, &b.source)));
    let mut groups: Vec<Vec<&Utterance>> = Vec::new();
    for utterance in ordered {
        let span = (utterance.start_ms, utterance.end_ms);
        let target = groups.iter_mut().rev().take(8).find(|g| {
            let start = g.iter().map(|u| u.start_ms).min().unwrap_or(0);
            let end = g.iter().map(|u| u.end_ms).max().unwrap_or(0);
            !g.iter().any(|u| u.source == utterance.source)
                && overlap_ratio((start, end), span) >= min_overlap
        });
        match target {
            Some(group) => group.push(utterance),
            None => groups.push(vec![utterance]),
        }
    }
    let mut turns = Vec::with_capacity(groups.len());
    for group in groups {
        let ballots: Vec<(String, f32)> = group
            .iter()
            .map(|u| (u.text.clone(), clean_weight(u.weight)))
            .collect();
        let ballot = vote(&ballots);
        if ballot.text.is_empty() {
            continue;
        }
        let (speaker, speaker_score) = pick_speaker(&group);
        let mut sources: Vec<String> = group.iter().map(|u| u.source.clone()).collect();
        sources.sort();
        turns.push(Turn {
            start_ms: group.iter().map(|u| u.start_ms).min().unwrap_or(0),
            end_ms: group.iter().map(|u| u.end_ms).max().unwrap_or(0),
            text: ballot.text,
            speaker,
            speaker_score,
            agreement: ballot.agreement,
            changed: ballot.changed,
            sources,
        });
    }
    Ok(turns)
}
