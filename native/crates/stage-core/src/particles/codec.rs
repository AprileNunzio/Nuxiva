use std::fmt;

pub const MAGIC: &[u8; 4] = b"NXPC";
pub const VERSION: u8 = 1;
pub const HEADER: usize = 12;
pub const MIN_POINTS: u32 = 256;
pub const MAX_POINTS: u32 = 65_536;
pub const FLAG_COLORS: u8 = 1;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParticleError {
    Spec(&'static str),
    Format(&'static str),
}

impl fmt::Display for ParticleError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Spec(why) => write!(f, "invalid particle spec: {why}"),
            Self::Format(why) => write!(f, "invalid particle blob: {why}"),
        }
    }
}

impl std::error::Error for ParticleError {}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Cloud {
    pub positions: Vec<[i16; 3]>,
    pub colors: Vec<[u8; 3]>,
}

impl Cloud {
    #[must_use]
    pub fn len(&self) -> usize {
        self.positions.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.positions.is_empty()
    }
}

#[must_use]
pub fn encode(cloud: &Cloud) -> Vec<u8> {
    let count = u32::try_from(cloud.len()).unwrap_or(u32::MAX);
    let colored = !cloud.colors.is_empty() && cloud.colors.len() == cloud.len();
    let mut out = Vec::with_capacity(HEADER.saturating_add(cloud.len().saturating_mul(9)));
    out.extend_from_slice(MAGIC);
    out.push(VERSION);
    out.push(if colored { FLAG_COLORS } else { 0 });
    out.extend_from_slice(&[0, 0]);
    out.extend_from_slice(&count.to_le_bytes());
    for p in &cloud.positions {
        for v in p {
            out.extend_from_slice(&v.to_le_bytes());
        }
    }
    if colored {
        for c in &cloud.colors {
            out.extend_from_slice(c);
        }
    }
    out
}

pub fn decode(blob: &[u8]) -> Result<Cloud, ParticleError> {
    let header = blob
        .get(..HEADER)
        .ok_or(ParticleError::Format("too short"))?;
    if header.get(..4) != Some(MAGIC.as_slice()) {
        return Err(ParticleError::Format("bad magic"));
    }
    if header.get(4) != Some(&VERSION) {
        return Err(ParticleError::Format("unsupported version"));
    }
    let flags = header.get(5).copied().unwrap_or(0);
    if flags & !FLAG_COLORS != 0 || header.get(6..8) != Some([0_u8, 0].as_slice()) {
        return Err(ParticleError::Format("unknown flags"));
    }
    let count_bytes: [u8; 4] = header
        .get(8..12)
        .and_then(|s| s.try_into().ok())
        .ok_or(ParticleError::Format("too short"))?;
    let count = u32::from_le_bytes(count_bytes);
    if count > MAX_POINTS {
        return Err(ParticleError::Format("too many points"));
    }
    let n = count as usize;
    let per = if flags & FLAG_COLORS == 0 { 6 } else { 9 };
    let expected = n
        .checked_mul(per)
        .and_then(|b| b.checked_add(HEADER))
        .ok_or(ParticleError::Format("size overflow"))?;
    if blob.len() != expected {
        return Err(ParticleError::Format("length mismatch"));
    }
    let body = blob.get(HEADER..).unwrap_or_default();
    let split = n.saturating_mul(6);
    let (pos, col) = body.split_at(split.min(body.len()));
    let positions = pos
        .chunks_exact(6)
        .map(|c| {
            let v = |i: usize| {
                let lo = c.get(i).copied().unwrap_or(0);
                let hi = c.get(i.saturating_add(1)).copied().unwrap_or(0);
                i16::from_le_bytes([lo, hi])
            };
            [v(0), v(2), v(4)]
        })
        .collect();
    let colors = col
        .chunks_exact(3)
        .map(|c| {
            [
                c.first().copied().unwrap_or(0),
                c.get(1).copied().unwrap_or(0),
                c.get(2).copied().unwrap_or(0),
            ]
        })
        .collect();
    Ok(Cloud { positions, colors })
}
