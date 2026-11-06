const UTTERANCE_FRAME: usize = 320;
const SILENCE: f64 = 1e-5;
const GATE_KNEE: f64 = 0.005;
const PEAK: f32 = 0.97;

fn percentile(sorted: &[f64], q: f64) -> f64 {
    let Some(last) = sorted.len().checked_sub(1) else {
        return 0.0;
    };
    #[allow(clippy::cast_precision_loss)]
    let pos = q / 100.0 * last as f64;
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    let lower = pos.floor() as usize;
    let upper = lower.saturating_add(1).min(last);
    #[allow(clippy::cast_precision_loss)]
    let frac = pos - lower as f64;
    let a = sorted.get(lower).copied().unwrap_or(0.0);
    let b = sorted.get(upper).copied().unwrap_or(a);
    a + (b - a) * frac
}

fn rms(chunk: &[f32]) -> f64 {
    if chunk.is_empty() {
        return 0.0;
    }
    let sum: f64 = chunk.iter().map(|v| f64::from(*v) * f64::from(*v)).sum();
    #[allow(clippy::cast_precision_loss)]
    let len = chunk.len() as f64;
    (sum / len).sqrt()
}

#[must_use]
pub fn voiced_rms(samples: &[f32]) -> f64 {
    let energy: Vec<f64> = if samples.len() >= UTTERANCE_FRAME {
        samples.chunks_exact(UTTERANCE_FRAME).map(rms).collect()
    } else {
        vec![rms(samples)]
    };
    let voiced: Vec<f64> = if energy.len() > 4 {
        let mut sorted = energy.clone();
        sorted.sort_by(f64::total_cmp);
        let cut = percentile(&sorted, 60.0);
        energy.into_iter().filter(|e| *e > cut).collect()
    } else {
        energy
    };
    if voiced.is_empty() {
        return 0.0;
    }
    #[allow(clippy::cast_precision_loss)]
    let len = voiced.len() as f64;
    voiced.iter().sum::<f64>() / len
}

#[must_use]
pub fn utterance_gain(samples: &[f32], target: f64, max_gain: f64) -> f64 {
    let level = voiced_rms(samples);
    if !level.is_finite() || level <= SILENCE {
        return 1.0;
    }
    let gate = (level / GATE_KNEE).powi(2).clamp(0.2, 1.0);
    max_gain.min(target / level) * gate
}

#[must_use]
pub fn normalize(samples: &[f32], target: f64, max_gain: f64) -> Vec<f32> {
    #[allow(clippy::cast_possible_truncation)]
    let gain = utterance_gain(samples, target, max_gain) as f32;
    samples
        .iter()
        .map(|v| {
            let y = if v.is_finite() { v * gain } else { 0.0 };
            PEAK * (y / PEAK).tanh()
        })
        .collect()
}
