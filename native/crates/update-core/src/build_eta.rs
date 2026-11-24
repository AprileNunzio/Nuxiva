use serde::{Deserialize, Serialize};

pub const MAX_UNITS: usize = 512;
const WINDOW: usize = 48;
const MIN_UNITS: u32 = 3;
const WINDOW_WEIGHT: f64 = 0.6;

#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct BuildSample {
    pub done: u32,
    pub total: u32,
    pub elapsed: f64,
    pub units: Vec<f64>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Confidence {
    Low,
    Medium,
    High,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct BuildEstimate {
    pub rate_per_min: Option<f64>,
    pub remaining: Option<u32>,
    pub eta: Option<f64>,
    pub eta_low: Option<f64>,
    pub eta_high: Option<f64>,
    pub confidence: Option<Confidence>,
}

fn count(n: usize) -> f64 {
    f64::from(u32::try_from(n).unwrap_or(u32::MAX))
}

fn round1(v: f64) -> f64 {
    (v * 10.0).round() / 10.0
}

fn clean_units(units: &[f64], elapsed: f64) -> Vec<f64> {
    let mut out: Vec<f64> = units
        .iter()
        .copied()
        .filter(|t| t.is_finite() && *t >= 0.0 && *t <= elapsed + 1.0)
        .collect();
    out.sort_by(f64::total_cmp);
    let skip = out.len().saturating_sub(MAX_UNITS);
    out.drain(..skip);
    out
}

fn window_rate(units: &[f64]) -> Option<f64> {
    let tail = units.get(units.len().saturating_sub(WINDOW)..)?;
    let (first, last) = (tail.first()?, tail.last()?);
    let span = last - first;
    (tail.len() >= 3 && span > 0.0).then(|| (count(tail.len()) - 1.0) / span)
}

fn variability(units: &[f64]) -> f64 {
    let tail = units
        .get(units.len().saturating_sub(WINDOW)..)
        .unwrap_or_default();
    let gaps: Vec<f64> = tail
        .windows(2)
        .map(|w| match w {
            [a, b] => b - a,
            _ => 0.0,
        })
        .collect();
    if gaps.len() < 2 {
        return 1.0;
    }
    let n = count(gaps.len());
    let mean = gaps.iter().sum::<f64>() / n;
    if mean <= 0.0 {
        return 1.0;
    }
    let var = gaps.iter().map(|g| (g - mean).powi(2)).sum::<f64>() / n;
    (var.sqrt() / mean).min(3.0)
}

fn confidence(rel: f64) -> Confidence {
    if rel < 0.25 {
        Confidence::High
    } else if rel < 0.5 {
        Confidence::Medium
    } else {
        Confidence::Low
    }
}

#[must_use]
pub fn estimate(sample: &BuildSample) -> BuildEstimate {
    let elapsed = if sample.elapsed.is_finite() && sample.elapsed > 0.0 {
        sample.elapsed
    } else {
        0.0
    };
    let units = clean_units(&sample.units, elapsed);
    let done = sample.done;
    let overall = (elapsed > 0.0 && done > 0).then(|| f64::from(done) / elapsed);
    let rate = match (window_rate(&units), overall) {
        (Some(w), Some(o)) => Some(WINDOW_WEIGHT * w + (1.0 - WINDOW_WEIGHT) * o),
        (w, o) => w.or(o),
    };
    let remaining = (sample.total > 0).then(|| sample.total.saturating_sub(done));
    let mut out = BuildEstimate {
        rate_per_min: rate.map(|r| round1(r * 60.0)),
        remaining,
        eta: None,
        eta_low: None,
        eta_high: None,
        confidence: None,
    };
    let (Some(rem), Some(r)) = (remaining, rate) else {
        return out;
    };
    if done < MIN_UNITS || r <= 0.0 {
        return out;
    }
    let base = f64::from(rem) / r;
    let since_last = units.last().map_or(0.0, |t| (elapsed - t).max(0.0));
    let eta = (base - since_last).max(base * 0.1);
    let rel =
        ((1.6 / f64::from(done).sqrt()).clamp(0.12, 0.9) + 0.3 * variability(&units)).min(1.5);
    out.eta = Some(round1(eta));
    out.eta_low = Some(round1((eta * (1.0 - 0.6 * rel)).max(0.0)));
    out.eta_high = Some(round1(eta * (1.0 + rel)));
    out.confidence = Some(confidence(rel));
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn steady(done: u32, total: u32, step: f64) -> BuildSample {
        let units: Vec<f64> = (1..=done).map(|i| f64::from(i) * step).collect();
        BuildSample {
            done,
            total,
            elapsed: f64::from(done) * step,
            units,
        }
    }

    #[test]
    fn steady_pace_gives_a_tight_estimate() {
        let est = estimate(&steady(200, 300, 2.0));
        assert_eq!(est.remaining, Some(100));
        assert_eq!(est.rate_per_min, Some(30.0));
        let eta = est.eta.unwrap_or_default();
        assert!((eta - 200.0).abs() < 1.0, "{eta}");
        assert_eq!(est.confidence, Some(Confidence::High));
        assert!(est.eta_low.unwrap_or_default() < eta && est.eta_high.unwrap_or_default() > eta);
    }

    #[test]
    fn few_units_mean_low_confidence_and_wide_range() {
        let est = estimate(&steady(4, 366, 3.0));
        assert_eq!(est.confidence, Some(Confidence::Low));
        let (low, high) = (
            est.eta_low.unwrap_or_default(),
            est.eta_high.unwrap_or_default(),
        );
        assert!(high > low * 2.0, "{low} {high}");
    }

    #[test]
    fn too_few_units_give_no_eta() {
        let est = estimate(&steady(2, 366, 3.0));
        assert_eq!(est.eta, None);
        assert!(est.rate_per_min.is_some());
    }

    #[test]
    fn unknown_total_gives_rate_only() {
        let est = estimate(&steady(50, 0, 1.0));
        assert_eq!(est.remaining, None);
        assert_eq!(est.eta, None);
        assert_eq!(est.rate_per_min, Some(60.0));
    }

    #[test]
    fn a_long_silence_never_drops_eta_below_a_floor() {
        let mut s = steady(100, 200, 1.0);
        s.elapsed = 10_000.0;
        let est = estimate(&s);
        assert!(est.eta.unwrap_or_default() > 0.0);
    }

    #[test]
    fn hostile_input_is_ignored() {
        let s = BuildSample {
            done: 10,
            total: 20,
            elapsed: f64::NAN,
            units: vec![f64::INFINITY, -1.0, f64::NAN, 1e12],
        };
        let est = estimate(&s);
        assert_eq!(est.rate_per_min, None);
        assert_eq!(est.eta, None);
    }

    #[test]
    fn completed_build_has_zero_eta() {
        let est = estimate(&steady(30, 30, 1.0));
        assert_eq!(est.remaining, Some(0));
        assert_eq!(est.eta, Some(0.0));
    }

    #[test]
    fn units_are_capped() {
        let units = clean_units(&[1.0; MAX_UNITS + 50], 2.0);
        assert_eq!(units.len(), MAX_UNITS);
    }
}
