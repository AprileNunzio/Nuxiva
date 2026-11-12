use crate::stft::{Spectrum, bin_hz};

pub const LOW_HZ: f32 = 300.0;
pub const HIGH_HZ: f32 = 4_000.0;
pub const PEAK_SHARE: f32 = 0.1;

#[derive(Debug, Clone, Copy, PartialEq, Default)]
pub struct SoundFrame {
    pub rms: f32,
    pub centroid_hz: f32,
    pub low_share: f32,
    pub flatness: f32,
    pub peak_hz: f32,
    pub peak_share: f32,
    pub peaks: usize,
}

fn rms(frame: &[f32]) -> f32 {
    if frame.is_empty() {
        return 0.0;
    }
    #[allow(clippy::cast_precision_loss)]
    let len = frame.len() as f32;
    (frame.iter().map(|v| v * v).sum::<f32>() / len).sqrt()
}

#[must_use]
pub fn describe(frame: &[f32], spectrum: &Spectrum) -> SoundFrame {
    let powers: Vec<(f32, f32)> = spectrum
        .iter()
        .enumerate()
        .skip(1)
        .map(|(k, c)| (bin_hz(k), c.norm_sqr()))
        .collect();
    let total: f32 = powers.iter().map(|(_, p)| p).sum();
    if total <= 1e-12 {
        return SoundFrame {
            rms: rms(frame),
            flatness: 1.0,
            ..SoundFrame::default()
        };
    }
    let centroid = powers.iter().map(|(hz, p)| hz * p).sum::<f32>() / total;
    let low: f32 = powers
        .iter()
        .filter(|(hz, _)| *hz < LOW_HZ)
        .map(|(_, p)| p)
        .sum();
    let band: Vec<(f32, f32)> = powers
        .iter()
        .copied()
        .filter(|(hz, _)| *hz >= LOW_HZ && *hz <= HIGH_HZ)
        .collect();
    let band_total: f32 = band.iter().map(|(_, p)| p).sum();
    #[allow(clippy::cast_precision_loss)]
    let count = band.len().max(1) as f32;
    let arith = band_total / count;
    let geo = (band.iter().map(|(_, p)| p.max(1e-12).ln()).sum::<f32>() / count).exp();
    let (peak_hz, peak_p) = band.iter().copied().fold((0.0_f32, 0.0_f32), |best, item| {
        if item.1 > best.1 { item } else { best }
    });
    let peaks = band
        .windows(3)
        .filter(|w| match w {
            [a, b, c] => b.1 > a.1 && b.1 >= c.1 && b.1 >= peak_p * PEAK_SHARE,
            _ => false,
        })
        .count();
    SoundFrame {
        rms: rms(frame),
        centroid_hz: centroid,
        low_share: (low / total).clamp(0.0, 1.0),
        flatness: if arith > 0.0 {
            (geo / arith).clamp(0.0, 1.0)
        } else {
            1.0
        },
        peak_hz,
        peak_share: if band_total > 0.0 {
            (peak_p / band_total).clamp(0.0, 1.0)
        } else {
            0.0
        },
        peaks,
    }
}
