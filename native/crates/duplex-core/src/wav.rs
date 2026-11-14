use crate::error::{DuplexError, DuplexResult};

pub const MAX_WAV_BYTES: usize = 16 * 1024 * 1024;
pub const MIN_RATE_HZ: u32 = 8_000;
pub const MAX_RATE_HZ: u32 = 48_000;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Pcm {
    pub rate_hz: u32,
    pub samples: Vec<i16>,
}

impl Pcm {
    #[must_use]
    pub fn duration_us(&self) -> u64 {
        samples_us(self.samples.len(), self.rate_hz)
    }

    #[must_use]
    pub fn to_bytes(&self) -> Vec<u8> {
        self.samples.iter().flat_map(|s| s.to_le_bytes()).collect()
    }
}

#[must_use]
pub fn samples_us(samples: usize, rate_hz: u32) -> u64 {
    let rate = u64::from(rate_hz.max(1));
    u64::try_from(samples)
        .unwrap_or(u64::MAX)
        .saturating_mul(1_000_000)
        .checked_div(rate)
        .unwrap_or(0)
}

fn le16(bytes: &[u8], at: usize) -> Option<u16> {
    let raw = bytes.get(at..at.checked_add(2)?)?;
    Some(u16::from_le_bytes(raw.try_into().ok()?))
}

fn le32(bytes: &[u8], at: usize) -> Option<u32> {
    let raw = bytes.get(at..at.checked_add(4)?)?;
    Some(u32::from_le_bytes(raw.try_into().ok()?))
}

struct Format {
    channels: usize,
    rate_hz: u32,
}

fn read_format(body: &[u8]) -> DuplexResult<Format> {
    let tag = le16(body, 0).ok_or(DuplexError::Parse)?;
    let channels = le16(body, 2).ok_or(DuplexError::Parse)?;
    let rate_hz = le32(body, 4).ok_or(DuplexError::Parse)?;
    let bits = le16(body, 14).ok_or(DuplexError::Parse)?;
    if tag != 1 || bits != 16 || !(1..=2).contains(&channels) {
        return Err(DuplexError::Invalid);
    }
    if !(MIN_RATE_HZ..=MAX_RATE_HZ).contains(&rate_hz) {
        return Err(DuplexError::Invalid);
    }
    Ok(Format {
        channels: usize::from(channels),
        rate_hz,
    })
}

fn to_mono(data: &[u8], channels: usize) -> Vec<i16> {
    let width = channels.saturating_mul(2);
    data.chunks_exact(width)
        .map(|frame| {
            let sum: i32 = frame
                .chunks_exact(2)
                .filter_map(|p| Some(i32::from(i16::from_le_bytes(p.try_into().ok()?))))
                .sum();
            let mean = sum
                .checked_div(i32::try_from(channels).unwrap_or(1))
                .unwrap_or(0);
            i16::try_from(mean).unwrap_or(0)
        })
        .collect()
}

pub fn parse_wav(bytes: &[u8]) -> DuplexResult<Pcm> {
    if bytes.len() > MAX_WAV_BYTES {
        return Err(DuplexError::TooLarge);
    }
    if bytes.get(..4) != Some(b"RIFF") || bytes.get(8..12) != Some(b"WAVE") {
        return Err(DuplexError::Invalid);
    }
    let mut at = 12usize;
    let mut format: Option<Format> = None;
    while let Some(id) = bytes.get(at..at.saturating_add(4)) {
        let declared = le32(bytes, at.saturating_add(4)).ok_or(DuplexError::Parse)?;
        let start = at.saturating_add(8);
        let available = bytes.len().saturating_sub(start);
        let size = usize::try_from(declared).unwrap_or(usize::MAX);
        if id == b"data" {
            let fmt = format.ok_or(DuplexError::Invalid)?;
            let take = size.min(available);
            let body = bytes
                .get(start..start.saturating_add(take))
                .ok_or(DuplexError::Parse)?;
            let samples = to_mono(body, fmt.channels);
            if samples.is_empty() {
                return Err(DuplexError::Invalid);
            }
            return Ok(Pcm {
                rate_hz: fmt.rate_hz,
                samples,
            });
        }
        if size > available {
            return Err(DuplexError::Parse);
        }
        if id == b"fmt " {
            let body = bytes
                .get(start..start.saturating_add(size))
                .ok_or(DuplexError::Parse)?;
            format = Some(read_format(body)?);
        }
        at = start.saturating_add(size).saturating_add(size & 1);
    }
    Err(DuplexError::Invalid)
}
