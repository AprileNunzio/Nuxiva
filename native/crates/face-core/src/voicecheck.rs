#![allow(clippy::cast_precision_loss)]

pub const MIN_RATE: u32 = 8_000;
pub const MAX_RATE: u32 = 48_000;
pub const MIN_SECONDS: f32 = 0.4;
pub const MAX_SECONDS: f32 = 6.0;
pub const FLOOR_DB: f32 = -120.0;
pub const TARGET_DB: f32 = -20.0;
pub const MAX_BOOST_DB: f32 = 24.0;
pub const MAX_CUT_DB: f32 = -12.0;
pub const HEADROOM_DB: f32 = -3.0;
const CLIP: i32 = 32_700;
const VOICED_OVER_NOISE_DB: f32 = 10.0;
const EDGE_S: f32 = 0.06;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VoiceError {
    Rate,
    Length,
}

impl VoiceError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Rate => "voice.check.rate",
            Self::Length => "voice.check.length",
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct VoiceReport {
    pub seconds: f32,
    pub voiced_seconds: f32,
    pub speech_db: f32,
    pub noise_db: f32,
    pub peak_db: f32,
    pub snr_db: f32,
    pub clipped_pct: f32,
    pub dc_offset: f32,
    pub lead_s: f32,
    pub tail_s: f32,
    pub gain_db: f32,
    pub score: f32,
    pub reasons: Vec<&'static str>,
}

fn db(v: f32) -> f32 {
    if v > 0.0 {
        (20.0 * v.log10()).max(FLOOR_DB)
    } else {
        FLOOR_DB
    }
}

fn pick(sorted: &[f32], num: usize, den: usize) -> f32 {
    let last = sorted.len().saturating_sub(1);
    let at = sorted
        .len()
        .saturating_mul(num)
        .checked_div(den)
        .unwrap_or(0)
        .min(last);
    sorted.get(at).copied().unwrap_or(0.0)
}

pub fn check(samples: &[i16], rate: u32) -> Result<VoiceReport, VoiceError> {
    if !(MIN_RATE..=MAX_RATE).contains(&rate) {
        return Err(VoiceError::Rate);
    }
    let seconds = samples.len() as f32 / rate as f32;
    if !(MIN_SECONDS..=MAX_SECONDS).contains(&seconds) {
        return Err(VoiceError::Length);
    }
    let window = usize::try_from(rate / 50).unwrap_or(160).max(1);
    let levels: Vec<f32> = samples
        .chunks(window)
        .map(|c| {
            let sum: f32 = c
                .iter()
                .map(|s| {
                    let v = f32::from(*s) / 32_768.0;
                    v * v
                })
                .sum();
            (sum / c.len().max(1) as f32).sqrt()
        })
        .collect();
    let mut sorted = levels.clone();
    sorted.sort_by(f32::total_cmp);
    let noise = pick(&sorted, 1, 10);
    let speech = pick(&sorted, 95, 100);
    let (speech_db, noise_db) = (db(speech), db(noise));
    let peak = samples
        .iter()
        .map(|s| i32::from(*s).abs())
        .max()
        .unwrap_or(0);
    let peak_db = db(peak as f32 / 32_768.0);
    let clipped = samples
        .iter()
        .filter(|s| i32::from(**s).abs() >= CLIP)
        .count();
    let clipped_pct = 100.0 * clipped as f32 / samples.len().max(1) as f32;
    let dc_offset =
        samples.iter().map(|s| f32::from(*s)).sum::<f32>() / samples.len().max(1) as f32 / 32_768.0;
    let voiced: Vec<bool> = levels
        .iter()
        .map(|l| db(*l) >= noise_db + VOICED_OVER_NOISE_DB && db(*l) > -60.0)
        .collect();
    let step = window as f32 / rate as f32;
    let voiced_seconds = voiced.iter().filter(|v| **v).count() as f32 * step;
    let lead_s = voiced.iter().take_while(|v| !**v).count() as f32 * step;
    let tail_s = voiced.iter().rev().take_while(|v| !**v).count() as f32 * step;
    let snr_db = speech_db - noise_db;
    let gain_db = (TARGET_DB - speech_db)
        .min(HEADROOM_DB - peak_db)
        .clamp(MAX_CUT_DB, MAX_BOOST_DB);
    let mut reasons = Vec::new();
    if clipped_pct >= 1.0 {
        reasons.push("clipped");
    }
    if speech_db <= -45.0 {
        reasons.push("weak");
    }
    if snr_db < 10.0 {
        reasons.push("noisy");
    }
    if voiced_seconds < 0.25 {
        reasons.push("short");
    }
    if voiced_seconds >= 0.25 && (lead_s < EDGE_S || tail_s < EDGE_S) {
        reasons.push("truncated");
    }
    if dc_offset.abs() > 0.05 {
        reasons.push("offset");
    }
    let level = 1.0 - ((speech_db - TARGET_DB).abs() / 25.0).min(1.0);
    let clean = (snr_db / 30.0).clamp(0.0, 1.0);
    let penalty = 18.0 * reasons.len() as f32;
    let score = (35.0 * level + 45.0 * clean + 20.0 * (voiced_seconds / 0.6).min(1.0) - penalty)
        .clamp(0.0, 100.0);
    Ok(VoiceReport {
        seconds,
        voiced_seconds,
        speech_db,
        noise_db,
        peak_db,
        snr_db,
        clipped_pct,
        dc_offset,
        lead_s,
        tail_s,
        gain_db,
        score,
        reasons,
    })
}
