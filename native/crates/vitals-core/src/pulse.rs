use realfft::RealFftPlanner;

pub const HEART_BAND: (f64, f64) = (0.7, 3.5);
pub const BREATH_BAND: (f64, f64) = (0.1, 0.7);
pub const HEART_RATE: f64 = 30.0;
pub const BREATH_RATE: f64 = 10.0;
pub const FFT_SIZE: usize = 4096;
pub const MAX_SAMPLES: usize = 8192;
const EPS: f64 = 1e-9;
const HEART_WIDTH: f64 = 0.1;
const BREATH_WIDTH: f64 = 0.04;

#[derive(Debug, Clone, Copy, PartialEq, Default)]
pub struct Estimate {
    pub per_minute: f64,
    pub quality: f64,
}

#[allow(clippy::cast_precision_loss)]
fn as_f64(n: usize) -> f64 {
    n as f64
}

#[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
fn steps(span: f64, rate: f64) -> usize {
    let count = (span * rate).ceil();
    if count.is_finite() && count > 0.0 {
        (count as usize).min(MAX_SAMPLES.saturating_mul(4))
    } else {
        0
    }
}

fn interp(ts: &[f64], values: &[f64], at: f64) -> f64 {
    let (Some(&first), Some(&last)) = (ts.first(), ts.last()) else {
        return 0.0;
    };
    if at <= first {
        return values.first().copied().unwrap_or(0.0);
    }
    if at >= last {
        return values.last().copied().unwrap_or(0.0);
    }
    let right = ts.partition_point(|t| *t <= at).max(1);
    let left = right.saturating_sub(1);
    match (
        ts.get(left),
        ts.get(right),
        values.get(left),
        values.get(right),
    ) {
        (Some(&t0), Some(&t1), Some(&v0), Some(&v1)) if t1 > t0 => {
            v0 + (v1 - v0) * (at - t0) / (t1 - t0)
        }
        (_, _, Some(&v0), _) => v0,
        _ => 0.0,
    }
}

#[must_use]
pub fn uniform(ts: &[f64], values: &[f64], rate: f64) -> Vec<f64> {
    let (Some(&first), Some(&last)) = (ts.first(), ts.last()) else {
        return Vec::new();
    };
    (0..steps(last - first, rate))
        .map(|i| interp(ts, values, first + as_f64(i) / rate))
        .collect()
}

#[must_use]
pub fn detrend(signal: &[f64]) -> Vec<f64> {
    let n = as_f64(signal.len());
    if signal.len() < 2 {
        return signal.iter().map(|_| 0.0).collect();
    }
    let mean_x = (n - 1.0) / 2.0;
    let mean_y = signal.iter().sum::<f64>() / n;
    let (mut sxy, mut sxx) = (0.0, 0.0);
    for (i, y) in signal.iter().enumerate() {
        let dx = as_f64(i) - mean_x;
        sxy += dx * (y - mean_y);
        sxx += dx * dx;
    }
    let slope = if sxx > 0.0 { sxy / sxx } else { 0.0 };
    let offset = mean_y - slope * mean_x;
    signal
        .iter()
        .enumerate()
        .map(|(i, y)| y - (slope * as_f64(i) + offset))
        .collect()
}

fn mean(values: &[f64]) -> f64 {
    if values.is_empty() {
        0.0
    } else {
        values.iter().sum::<f64>() / as_f64(values.len())
    }
}

fn std(values: &[f64]) -> f64 {
    let m = mean(values);
    mean(&values.iter().map(|v| (v - m) * (v - m)).collect::<Vec<_>>()).sqrt()
}

#[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
#[must_use]
pub fn pos(rgb: &[[f64; 3]], rate: f64) -> Vec<f64> {
    let window = ((1.6 * rate).round().max(2.0)) as usize;
    let mut out = vec![0.0; rgb.len()];
    if rgb.len() < window {
        return out;
    }
    for (start, chunk) in rgb.windows(window).enumerate() {
        let means: [f64; 3] = std::array::from_fn(|c| {
            mean(
                &chunk
                    .iter()
                    .map(|p| p.get(c).copied().unwrap_or(0.0))
                    .collect::<Vec<_>>(),
            ) + EPS
        });
        let [mr, mg, mb] = means;
        let s1: Vec<f64> = chunk.iter().map(|[_, g, b]| g / mg - b / mb).collect();
        let s2: Vec<f64> = chunk
            .iter()
            .map(|[r, g, b]| g / mg + b / mb - 2.0 * r / mr)
            .collect();
        let alpha = std(&s1) / (std(&s2) + EPS);
        let mixed: Vec<f64> = s1.iter().zip(&s2).map(|(a, b)| a + alpha * b).collect();
        let centre = mean(&mixed);
        for (slot, value) in out.iter_mut().skip(start).zip(&mixed) {
            *slot += value - centre;
        }
    }
    out
}

fn hanning(size: usize) -> Vec<f64> {
    if size < 2 {
        return vec![1.0; size];
    }
    let span = as_f64(size.saturating_sub(1));
    (0..size)
        .map(|i| 0.5 - 0.5 * (2.0 * std::f64::consts::PI * as_f64(i) / span).cos())
        .collect()
}

fn band_sum(power: &[f64], step: f64, band: (f64, f64), around: Option<(f64, f64)>) -> f64 {
    power
        .iter()
        .enumerate()
        .filter(|(i, _)| {
            let f = as_f64(*i) * step;
            f >= band.0 && f <= band.1 && around.is_none_or(|(c, w)| (f - c).abs() <= w)
        })
        .map(|(_, p)| *p)
        .sum()
}

#[must_use]
pub fn dominant(signal: &[f64], rate: f64, band: (f64, f64), width: f64) -> Estimate {
    if signal.len() < 8
        || signal.len() > MAX_SAMPLES.saturating_mul(4)
        || !signal.iter().all(|v| v.is_finite())
        || rate <= 0.0
    {
        return Estimate::default();
    }
    let size = FFT_SIZE.max(signal.len());
    let mut input: Vec<f64> = detrend(signal)
        .iter()
        .zip(hanning(signal.len()))
        .map(|(v, w)| v * w)
        .collect();
    input.resize(size, 0.0);
    let plan = RealFftPlanner::<f64>::new().plan_fft_forward(size);
    let mut spectrum = plan.make_output_vec();
    if plan.process(&mut input, &mut spectrum).is_err() {
        return Estimate::default();
    }
    let power: Vec<f64> = spectrum
        .iter()
        .map(realfft::num_complex::Complex::norm_sqr)
        .collect();
    let step = rate / as_f64(size);
    let total = band_sum(&power, step, band, None);
    if total <= EPS {
        return Estimate::default();
    }
    let mut index = 0usize;
    let mut best = 0.0;
    for (i, p) in power.iter().enumerate() {
        let f = as_f64(i) * step;
        if f >= band.0 && f <= band.1 && *p > best {
            best = *p;
            index = i;
        }
    }
    let mut peak = as_f64(index) * step;
    if index > 0 {
        if let (Some(&a), Some(&b), Some(&c)) = (
            power.get(index.saturating_sub(1)),
            power.get(index),
            power.get(index.saturating_add(1)),
        ) {
            let denom = a - 2.0 * b + c;
            if denom.abs() > EPS {
                peak += 0.5 * (a - c) / denom * step;
            }
        }
    }
    let quality = (band_sum(&power, step, band, Some((peak, width)))
        + band_sum(&power, step, band, Some((2.0 * peak, width))))
        / total;
    Estimate {
        per_minute: peak * 60.0,
        quality: quality.min(1.0),
    }
}

fn span(ts: &[f64]) -> f64 {
    match (ts.first(), ts.last()) {
        (Some(a), Some(b)) => b - a,
        _ => 0.0,
    }
}

fn ordered(ts: &[f64]) -> bool {
    ts.iter().all(|t| t.is_finite()) && ts.windows(2).all(|w| matches!(w, [a, b] if a <= b))
}

#[must_use]
pub fn heart_rate(ts: &[f64], rgb: &[[f64; 3]]) -> Estimate {
    if ts.len() < 16
        || ts.len() != rgb.len()
        || ts.len() > MAX_SAMPLES
        || !ordered(ts)
        || span(ts) < 4.0
    {
        return Estimate::default();
    }
    let channels: [Vec<f64>; 3] = std::array::from_fn(|c| {
        uniform(
            ts,
            &rgb.iter()
                .map(|p| p.get(c).copied().unwrap_or(0.0))
                .collect::<Vec<_>>(),
            HEART_RATE,
        )
    });
    let rows = channels.first().map_or(0, Vec::len);
    if rows < 16 || channels.iter().any(|c| mean(c) <= 1.0) {
        return Estimate::default();
    }
    let even: Vec<[f64; 3]> = (0..rows)
        .map(|i| {
            std::array::from_fn(|c| {
                channels
                    .get(c)
                    .and_then(|v| v.get(i))
                    .copied()
                    .unwrap_or(0.0)
            })
        })
        .collect();
    dominant(&pos(&even, HEART_RATE), HEART_RATE, HEART_BAND, HEART_WIDTH)
}

#[must_use]
pub fn breath_rate(ts: &[f64], shift: &[f64]) -> Estimate {
    if ts.len() < 32
        || ts.len() != shift.len()
        || ts.len() > MAX_SAMPLES
        || !ordered(ts)
        || span(ts) < 15.0
    {
        return Estimate::default();
    }
    let even = uniform(ts, shift, BREATH_RATE);
    let diff: Vec<f64> = even
        .windows(2)
        .filter_map(|w| match w {
            [a, b] => Some(b - a),
            _ => None,
        })
        .collect();
    dominant(&diff, BREATH_RATE, BREATH_BAND, BREATH_WIDTH)
}

#[allow(clippy::cast_possible_truncation)]
#[must_use]
pub fn agreed(seen: &[Option<f64>], window: usize, spread: f64) -> Option<i64> {
    if window == 0 || seen.len() < window {
        return None;
    }
    let mut last: Vec<f64> = seen
        .iter()
        .skip(seen.len().saturating_sub(window))
        .copied()
        .collect::<Option<Vec<f64>>>()?;
    if last.iter().any(|v| !v.is_finite()) {
        return None;
    }
    last.sort_by(f64::total_cmp);
    let (lo, hi) = (*last.first()?, *last.last()?);
    if hi - lo > spread {
        return None;
    }
    let half = last.len() / 2;
    let median = if last.len() % 2 == 1 {
        *last.get(half)?
    } else {
        f64::midpoint(*last.get(half.saturating_sub(1))?, *last.get(half)?)
    };
    let rounded = median.round_ties_even();
    (rounded.abs() < 1e6).then_some(rounded as i64)
}
