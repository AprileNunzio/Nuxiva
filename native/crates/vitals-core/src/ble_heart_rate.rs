pub const MAX_FRAME_BYTES: usize = 512;
const MAX_BPM: u16 = 250;
const MAX_RMSSD_MS: f64 = 300.0;
const FLAG_UINT16: u8 = 0x01;
const FLAG_ENERGY: u8 = 0x08;
const FLAG_RR: u8 = 0x10;

#[derive(Debug, Clone, Copy, PartialEq, Default)]
pub struct HeartRateSample {
    pub heart_rate_bpm: Option<f64>,
    pub hrv_rmssd_ms: Option<f64>,
}

fn read_u16(frame: &[u8], at: usize) -> Option<u16> {
    let lo = *frame.get(at)?;
    let hi = *frame.get(at.checked_add(1)?)?;
    Some(u16::from_le_bytes([lo, hi]))
}

fn rr_intervals_ms(frame: &[u8], start: usize) -> Vec<f64> {
    frame
        .get(start..)
        .unwrap_or_default()
        .chunks_exact(2)
        .filter_map(|pair| match pair {
            [lo, hi] => Some(f64::from(u16::from_le_bytes([*lo, *hi])) * 1000.0 / 1024.0),
            _ => None,
        })
        .filter(|ms| *ms > 0.0)
        .collect()
}

#[allow(clippy::cast_precision_loss)]
fn rmssd(intervals: &[f64]) -> Option<f64> {
    let squares: Vec<f64> = intervals
        .windows(2)
        .filter_map(|pair| match pair {
            [a, b] => Some((b - a) * (b - a)),
            _ => None,
        })
        .collect();
    if squares.is_empty() {
        return None;
    }
    let value = (squares.iter().sum::<f64>() / squares.len() as f64).sqrt();
    (value <= MAX_RMSSD_MS).then_some(value)
}

#[must_use]
pub fn parse_heart_rate_measurement(frame: &[u8]) -> HeartRateSample {
    if frame.len() < 2 || frame.len() > MAX_FRAME_BYTES {
        return HeartRateSample::default();
    }
    let flags = frame.first().copied().unwrap_or_default();
    let wide = flags & FLAG_UINT16 != 0;
    let bpm = if wide {
        read_u16(frame, 1)
    } else {
        frame.get(1).copied().map(u16::from)
    };
    let Some(bpm) = bpm.filter(|value| (1..=MAX_BPM).contains(value)) else {
        return HeartRateSample::default();
    };
    let mut start: usize = if wide { 3 } else { 2 };
    if flags & FLAG_ENERGY != 0 {
        start = start.saturating_add(2);
    }
    let intervals = if flags & FLAG_RR != 0 {
        rr_intervals_ms(frame, start)
    } else {
        Vec::new()
    };
    let hrv = match intervals.as_slice() {
        [] => None,
        [single] => Some((single * 0.08).clamp(5.0, MAX_RMSSD_MS)),
        many => rmssd(many),
    };
    HeartRateSample {
        heart_rate_bpm: Some(f64::from(bpm)),
        hrv_rmssd_ms: hrv,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_uint8_bpm_with_single_rr() {
        let sample = parse_heart_rate_measurement(&[0x10, 0x48, 0x10, 0x02]);
        assert_eq!(sample.heart_rate_bpm, Some(72.0));
        assert!(sample.hrv_rmssd_ms.is_some());
    }

    #[test]
    fn parses_uint16_bpm() {
        let sample = parse_heart_rate_measurement(&[0x01, 0x78, 0x00]);
        assert_eq!(sample.heart_rate_bpm, Some(120.0));
        assert_eq!(sample.hrv_rmssd_ms, None);
    }

    #[test]
    fn computes_rmssd_and_skips_energy_field() {
        let sample = parse_heart_rate_measurement(&[0x18, 60, 0xFF, 0xFF, 0x00, 0x04, 0x20, 0x04]);
        let expected = (f64::from(0x0420_u16) - f64::from(0x0400_u16)) * 1000.0 / 1024.0;
        assert_eq!(sample.heart_rate_bpm, Some(60.0));
        assert!(
            sample
                .hrv_rmssd_ms
                .is_some_and(|v| (v - expected).abs() < 1e-9)
        );
    }

    #[test]
    fn rejects_out_of_range_and_truncated() {
        assert_eq!(
            parse_heart_rate_measurement(&[0x00, 0x00]),
            HeartRateSample::default()
        );
        assert_eq!(
            parse_heart_rate_measurement(&[0x01, 0xFF, 0xFF]),
            HeartRateSample::default()
        );
        assert_eq!(
            parse_heart_rate_measurement(&[0x01, 0x48]),
            HeartRateSample::default()
        );
        assert_eq!(
            parse_heart_rate_measurement(&[0x00]),
            HeartRateSample::default()
        );
    }

    #[test]
    fn rejects_oversized_frames() {
        let frame = vec![0x10_u8; MAX_FRAME_BYTES.saturating_add(1)];
        assert_eq!(
            parse_heart_rate_measurement(&frame),
            HeartRateSample::default()
        );
    }

    #[test]
    fn ignores_trailing_odd_byte_in_rr() {
        let sample = parse_heart_rate_measurement(&[0x10, 0x48, 0x00, 0x04, 0x07]);
        assert!(sample.hrv_rmssd_ms.is_some());
    }
}
