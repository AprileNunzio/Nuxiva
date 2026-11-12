use crate::error::GaitError;
use crate::observation::GaitObservation;
use crate::signature::{GAIT_DIM, GaitSignature};

const MIN_SAMPLES: usize = 5;
const MIN_DURATION_MS: u64 = 400;

#[must_use]
fn mean(vals: &[f32]) -> f32 {
    if vals.is_empty() {
        return 0.0;
    }
    let mut sum = 0.0_f32;
    for v in vals {
        sum += *v;
    }
    #[allow(clippy::cast_precision_loss)]
    (sum / vals.len() as f32)
}

#[must_use]
fn variance(vals: &[f32], avg: f32) -> f32 {
    if vals.len() < 2 {
        return 0.0;
    }
    let mut sum_sq = 0.0_f32;
    for v in vals {
        let diff = *v - avg;
        sum_sq += diff * diff;
    }
    #[allow(clippy::cast_precision_loss)]
    (sum_sq / vals.len() as f32)
}

fn estimate_period_lag(centered_y: &[f32]) -> (usize, f32) {
    let n = centered_y.len();
    if n < 4 {
        return (2, 0.3);
    }
    let mut best_lag = 2_usize;
    let mut best_corr = -1.0_f32;
    let max_lag = (n / 2).max(2);
    for lag in 1..=max_lag {
        let mut num = 0.0_f32;
        let mut den_a = 0.0_f32;
        let mut den_b = 0.0_f32;
        for i in 0..n.saturating_sub(lag) {
            let a = centered_y.get(i).copied().unwrap_or(0.0);
            let b = centered_y
                .get(i.saturating_add(lag))
                .copied()
                .unwrap_or(0.0);
            num += a * b;
            den_a += a * a;
            den_b += b * b;
        }
        let denom = (den_a * den_b).sqrt();
        let corr = if denom > 1e-6 { num / denom } else { 0.0 };
        if corr > best_corr && lag >= 2 {
            best_corr = corr;
            best_lag = lag;
        }
    }
    (best_lag, best_corr.clamp(0.0, 1.0))
}

fn compute_harmonics(signal: &[f32]) -> [f32; 8] {
    let mut bins = [0.0_f32; 8];
    let n = signal.len();
    if n == 0 {
        return bins;
    }
    #[allow(clippy::cast_precision_loss)]
    let n_f = n as f32;
    for (k, slot) in bins.iter_mut().enumerate() {
        let mut sum = 0.0_f32;
        #[allow(clippy::cast_precision_loss)]
        let k_f = k as f32;
        for (i, val) in signal.iter().enumerate() {
            #[allow(clippy::cast_precision_loss)]
            let i_f = i as f32;
            let angle = (std::f32::consts::PI / n_f) * (i_f + 0.5) * (k_f + 1.0);
            sum += *val * angle.cos();
        }
        *slot = (sum.abs() / n_f).clamp(0.0, 1.0);
    }
    bins
}

#[allow(clippy::too_many_lines, clippy::cast_precision_loss)]
pub fn extract_signature(observations: &[GaitObservation]) -> Result<GaitSignature, GaitError> {
    if observations.len() < MIN_SAMPLES {
        return Err(GaitError::InsufficientSamples);
    }
    for obs in observations {
        obs.validate()?;
    }
    let mut sorted = observations.to_vec();
    sorted.sort_by_key(|o| o.timestamp_ms);
    let first_t = sorted.first().map_or(0, |o| o.timestamp_ms);
    let last_t = sorted.last().map_or(0, |o| o.timestamp_ms);
    let duration_ms = last_t.saturating_sub(first_t);
    if duration_ms < MIN_DURATION_MS {
        return Err(GaitError::InsufficientDuration);
    }
    let duration_s = (duration_ms as f32 / 1000.0).max(0.1);
    let heights: Vec<f32> = sorted.iter().map(|o| o.height).collect();
    let widths: Vec<f32> = sorted.iter().map(|o| o.width).collect();
    let centers_x: Vec<f32> = sorted.iter().map(GaitObservation::center_x).collect();
    let centers_y: Vec<f32> = sorted.iter().map(GaitObservation::center_y).collect();
    let aspect_ratios: Vec<f32> = sorted.iter().map(GaitObservation::aspect_ratio).collect();
    let mean_h = mean(&heights).max(1.0);
    let mean_w = mean(&widths).max(1.0);
    let mean_y = mean(&centers_y);
    let mean_ar = mean(&aspect_ratios);
    let var_ar = variance(&aspect_ratios, mean_ar);
    let centered_y: Vec<f32> = centers_y.iter().map(|y| *y - mean_y).collect();
    let (best_lag, corr_score) = estimate_period_lag(&centered_y);
    let dt_step_s = (duration_s / sorted.len() as f32) * (best_lag as f32);
    let cadence_spm = if dt_step_s > 0.05 {
        (60.0 / dt_step_s).clamp(30.0, 240.0)
    } else {
        100.0
    };
    let norm_cadence = (cadence_spm / 120.0).clamp(0.1, 2.0);
    let first_x = centers_x.first().copied().unwrap_or(0.0);
    let last_x = centers_x.last().copied().unwrap_or(0.0);
    let first_y = centers_y.first().copied().unwrap_or(0.0);
    let last_y = centers_y.last().copied().unwrap_or(0.0);
    let travel_dx = last_x - first_x;
    let travel_dy = last_y - first_y;
    let travel_dist = (travel_dx * travel_dx + travel_dy * travel_dy).sqrt();
    let norm_speed = ((travel_dist / mean_h) / duration_s).clamp(0.0, 5.0);
    let num_steps = (duration_s * (cadence_spm / 60.0)).max(1.0);
    let rel_stride = ((travel_dist / num_steps) / mean_h).clamp(0.0, 2.0);
    let min_y = centers_y.iter().copied().fold(f32::INFINITY, f32::min);
    let max_y = centers_y.iter().copied().fold(f32::NEG_INFINITY, f32::max);
    let vert_osc = ((max_y - min_y) / mean_h).clamp(0.0, 1.0);
    let min_x = centers_x.iter().copied().fold(f32::INFINITY, f32::min);
    let max_x = centers_x.iter().copied().fold(f32::NEG_INFINITY, f32::max);
    let lat_sway = ((max_x - min_x) / mean_w).clamp(0.0, 1.0);
    let mut odd_amp = 0.0_f32;
    let mut even_amp = 0.0_f32;
    for (i, c) in centered_y.iter().enumerate() {
        if i % 2 == 0 {
            even_amp += c.abs();
        } else {
            odd_amp += c.abs();
        }
    }
    let symmetry = if even_amp.max(odd_amp) > 1e-4 {
        (even_amp.min(odd_amp) / even_amp.max(odd_amp)).clamp(0.0, 1.0)
    } else {
        0.5
    };
    let norm_signal: Vec<f32> = centered_y
        .iter()
        .map(|y| (*y / mean_h).clamp(-1.0, 1.0))
        .collect();
    let harmonics = compute_harmonics(&norm_signal);
    let mut features = [0.0_f32; GAIT_DIM];
    if let Some(s) = features.get_mut(0) {
        *s = norm_cadence;
    }
    if let Some(s) = features.get_mut(1) {
        *s = rel_stride;
    }
    if let Some(s) = features.get_mut(2) {
        *s = vert_osc;
    }
    if let Some(s) = features.get_mut(3) {
        *s = lat_sway;
    }
    if let Some(s) = features.get_mut(4) {
        *s = symmetry;
    }
    if let Some(s) = features.get_mut(5) {
        *s = mean_ar.clamp(0.0, 2.0);
    }
    if let Some(s) = features.get_mut(6) {
        *s = var_ar.clamp(0.0, 1.0);
    }
    if let Some(s) = features.get_mut(7) {
        *s = norm_speed;
    }
    for (idx, h) in harmonics.iter().enumerate() {
        if let Some(s) = features.get_mut(8_usize.saturating_add(idx)) {
            *s = *h;
        }
    }
    let sample_score = (sorted.len() as f32 / 20.0).clamp(0.2, 1.0);
    let dur_score = (duration_s / 2.0).clamp(0.3, 1.0);
    let confidence = (sample_score * 0.4 + dur_score * 0.3 + corr_score * 0.3).clamp(0.1, 1.0);
    Ok(GaitSignature::new(features, sorted.len(), confidence))
}
