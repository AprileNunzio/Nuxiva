use crate::stft::{Spectrum, Stft, bin_hz};

const SAMPLE_RATE: f32 = 16_000.0;
const LAG_MIN: usize = 40;
const LAG_MAX: usize = 228;
const BAND_LOW: f32 = 300.0;
const BAND_HIGH: f32 = 3_400.0;
const FLAT_HIGH: f32 = 4_000.0;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct FrameFeatures {
    pub rms: f32,
    pub band_power: f32,
    pub flatness: f32,
    pub harmonicity: f32,
    pub pitch_hz: f32,
}

fn rms(frame: &[f32]) -> f32 {
    if frame.is_empty() {
        return 0.0;
    }
    #[allow(clippy::cast_precision_loss)]
    let len = frame.len() as f32;
    (frame.iter().map(|v| v * v).sum::<f32>() / len).sqrt()
}

fn harmonicity(window: &[f32]) -> (f32, f32) {
    let mut best = 0.0_f32;
    let mut best_lag = 0_usize;
    for lag in LAG_MIN..=LAG_MAX {
        let Some(tail) = window.get(lag..) else {
            break;
        };
        let (mut cross, mut a, mut b) = (0.0_f32, 0.0_f32, 0.0_f32);
        for (x, y) in window.iter().zip(tail) {
            cross += x * y;
            a += x * x;
            b += y * y;
        }
        let score = cross / (a * b).sqrt().max(1e-12);
        if score > best {
            best = score;
            best_lag = lag;
        }
    }
    #[allow(clippy::cast_precision_loss)]
    let pitch = if best_lag > 0 {
        SAMPLE_RATE / best_lag as f32
    } else {
        0.0
    };
    (best.clamp(0.0, 1.0), pitch)
}

pub fn analyze(
    frame: &[f32],
    window: &[f32],
    stft: &mut Stft,
    spectrum: &mut Spectrum,
) -> FrameFeatures {
    let powers: Vec<(f32, f32)> = if stft.analyze(window, spectrum) {
        spectrum
            .iter()
            .enumerate()
            .map(|(k, c)| (bin_hz(k), c.norm_sqr()))
            .collect()
    } else {
        Vec::new()
    };
    let band: Vec<f32> = powers
        .iter()
        .filter(|(hz, _)| *hz >= BAND_LOW && *hz <= BAND_HIGH)
        .map(|(_, p)| *p)
        .collect();
    let flat: Vec<f32> = powers
        .iter()
        .filter(|(hz, _)| *hz >= BAND_LOW && *hz <= FLAT_HIGH)
        .map(|(_, p)| p.max(1e-12))
        .collect();
    #[allow(clippy::cast_precision_loss)]
    let count = flat.len().max(1) as f32;
    let arith = flat.iter().sum::<f32>() / count;
    let geo = (flat.iter().map(|p| p.ln()).sum::<f32>() / count).exp();
    let (harmonicity, pitch_hz) = harmonicity(window);
    FrameFeatures {
        rms: rms(frame),
        band_power: band.iter().sum(),
        flatness: if arith > 0.0 {
            (geo / arith).clamp(0.0, 1.0)
        } else {
            1.0
        },
        harmonicity,
        pitch_hz,
    }
}
