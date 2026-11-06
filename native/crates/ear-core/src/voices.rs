use crate::speaker::{dot, unit};

pub const MAX_VOICES: usize = 8;
const JOIN: f32 = 0.55;
const ACTIVE_S: f64 = 120.0;
const FORGET_S: f64 = 1_800.0;
const ADAPT: f32 = 0.2;

#[derive(Debug, Clone)]
struct Voice {
    label: u32,
    centre: Vec<f32>,
    known: Option<String>,
    last_seen: f64,
    turns: u32,
}

#[derive(Debug, Clone, PartialEq)]
pub struct TurnInfo {
    pub label: u32,
    pub known: Option<String>,
    pub new_voice: bool,
    pub same_as_last: bool,
    pub active_voices: usize,
    pub similarity: f32,
}

#[derive(Debug, Clone, Default)]
pub struct VoiceTracker {
    voices: Vec<Voice>,
    next_label: u32,
    last: Option<u32>,
}

impl VoiceTracker {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    fn forget_old(&mut self, now: f64) {
        self.voices.retain(|v| now - v.last_seen <= FORGET_S);
        if self.voices.len() > MAX_VOICES {
            self.voices
                .sort_by(|a, b| b.last_seen.total_cmp(&a.last_seen));
            self.voices.truncate(MAX_VOICES);
        }
    }

    #[must_use]
    pub fn active(&self, now: f64) -> usize {
        self.voices
            .iter()
            .filter(|v| now - v.last_seen <= ACTIVE_S)
            .count()
    }

    pub fn observe(&mut self, probe: &[f32], now: f64, known: Option<&str>) -> Option<TurnInfo> {
        if probe.is_empty() || probe.iter().any(|v| !v.is_finite()) || !now.is_finite() {
            return None;
        }
        self.forget_old(now);
        let probe = unit(probe);
        let by_name = known.and_then(|k| {
            self.voices
                .iter()
                .position(|v| v.known.as_deref() == Some(k))
        });
        let by_sound = self
            .voices
            .iter()
            .enumerate()
            .filter(|(_, v)| v.centre.len() == probe.len())
            .map(|(i, v)| (i, dot(&v.centre, &probe)))
            .filter(|(i, s)| {
                *s >= JOIN
                    && known.is_none_or(|k| {
                        self.voices
                            .get(*i)
                            .and_then(|v| v.known.as_deref())
                            .is_none_or(|n| n == k)
                    })
            })
            .max_by(|a, b| a.1.total_cmp(&b.1));
        let found = by_name.map(|i| (i, 1.0)).or(by_sound);
        let (index, similarity, new_voice) = if let Some((i, s)) = found {
            (i, s, false)
        } else {
            let label = self.next_label;
            self.next_label = self.next_label.saturating_add(1);
            self.voices.push(Voice {
                label,
                centre: probe.clone(),
                known: None,
                last_seen: now,
                turns: 0,
            });
            if self.voices.len() > MAX_VOICES {
                self.voices
                    .sort_by(|a, b| b.last_seen.total_cmp(&a.last_seen));
                self.voices.truncate(MAX_VOICES);
            }
            let at = self.voices.iter().position(|v| v.label == label)?;
            (at, 1.0, true)
        };
        let voice = self.voices.get_mut(index)?;
        if !new_voice && voice.centre.len() == probe.len() {
            let blended: Vec<f32> = voice
                .centre
                .iter()
                .zip(&probe)
                .map(|(c, p)| (1.0 - ADAPT) * c + ADAPT * p)
                .collect();
            voice.centre = unit(&blended);
        }
        if let Some(k) = known {
            voice.known = Some(k.to_owned());
        }
        voice.last_seen = now;
        voice.turns = voice.turns.saturating_add(1);
        let label = voice.label;
        let known_name = voice.known.clone();
        let same_as_last = self.last == Some(label);
        self.last = Some(label);
        Some(TurnInfo {
            label,
            known: known_name,
            new_voice,
            same_as_last,
            active_voices: self.active(now),
            similarity,
        })
    }
}

#[must_use]
pub fn split_turns(windows: &[Vec<f32>], change: f32) -> Vec<usize> {
    let change = if change.is_finite() {
        change.clamp(0.0, 1.0)
    } else {
        JOIN
    };
    let mut centres: Vec<Vec<f32>> = Vec::new();
    let mut labels = Vec::with_capacity(windows.len());
    let mut current: Option<usize> = None;
    for window in windows {
        if window.is_empty() || window.iter().any(|v| !v.is_finite()) {
            labels.push(current.unwrap_or(0));
            continue;
        }
        let probe = unit(window);
        let stay = current
            .and_then(|c| centres.get(c).map(|centre| (c, dot(centre, &probe))))
            .filter(|(_, s)| *s >= change);
        let chosen = stay.map(|(c, _)| c).or_else(|| {
            centres
                .iter()
                .enumerate()
                .map(|(i, c)| (i, dot(c, &probe)))
                .filter(|(_, s)| *s >= change)
                .max_by(|a, b| a.1.total_cmp(&b.1))
                .map(|(i, _)| i)
        });
        let index = if let Some(i) = chosen {
            if let Some(centre) = centres.get_mut(i) {
                let blended: Vec<f32> = centre
                    .iter()
                    .zip(&probe)
                    .map(|(c, p)| 0.7 * c + 0.3 * p)
                    .collect();
                *centre = unit(&blended);
            }
            i
        } else {
            centres.push(probe);
            centres.len().saturating_sub(1)
        };
        current = Some(index);
        labels.push(index);
    }
    labels
}
