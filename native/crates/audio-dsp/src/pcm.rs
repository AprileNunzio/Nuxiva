pub const MAX_FRAME_BYTES: usize = 1_048_576;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PcmError {
    FrameTooLarge,
}

impl std::fmt::Display for PcmError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::FrameTooLarge => f.write_str("audio.pcm.frame_too_large"),
        }
    }
}

impl std::error::Error for PcmError {}

pub fn decode_le(bytes: &[u8]) -> Result<Vec<i16>, PcmError> {
    if bytes.len() > MAX_FRAME_BYTES {
        return Err(PcmError::FrameTooLarge);
    }
    Ok(bytes
        .chunks_exact(2)
        .map(|pair| match pair {
            [lo, hi] => i16::from_le_bytes([*lo, *hi]),
            _ => 0,
        })
        .collect())
}

pub fn decode_f32_le(bytes: &[u8]) -> Result<Vec<f32>, PcmError> {
    if bytes.len() > MAX_FRAME_BYTES.saturating_mul(4) {
        return Err(PcmError::FrameTooLarge);
    }
    Ok(bytes
        .chunks_exact(4)
        .map(|quad| match quad {
            [a, b, c, d] => {
                let value = f32::from_le_bytes([*a, *b, *c, *d]);
                if value.is_finite() { value } else { 0.0 }
            }
            _ => 0.0,
        })
        .collect())
}

#[must_use]
pub fn encode_le(samples: &[i16]) -> Vec<u8> {
    samples.iter().flat_map(|s| s.to_le_bytes()).collect()
}

#[must_use]
pub fn to_unit_f32(samples: &[i16]) -> Vec<f32> {
    samples.iter().map(|s| f32::from(*s) / 32_768.0).collect()
}

#[must_use]
pub fn from_unit_f32(samples: &[f32]) -> Vec<i16> {
    samples
        .iter()
        .map(|s| {
            let scaled = (s.clamp(-1.0, 1.0) * 32_767.0).round();
            #[allow(clippy::cast_possible_truncation)]
            let value = scaled as i16;
            value
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_preserves_samples() -> Result<(), PcmError> {
        let samples = [i16::MIN, -1, 0, 1, i16::MAX];
        assert_eq!(decode_le(&encode_le(&samples))?, samples);
        Ok(())
    }

    #[test]
    fn odd_trailing_byte_is_dropped() -> Result<(), PcmError> {
        assert_eq!(decode_le(&[1, 0, 9])?, vec![1]);
        Ok(())
    }

    #[test]
    fn oversized_frame_is_rejected() {
        let huge = vec![0_u8; MAX_FRAME_BYTES.saturating_add(2)];
        assert_eq!(decode_le(&huge), Err(PcmError::FrameTooLarge));
    }

    #[test]
    fn non_finite_floats_are_zeroed() -> Result<(), PcmError> {
        let mut raw = f32::NAN.to_le_bytes().to_vec();
        raw.extend_from_slice(&0.5_f32.to_le_bytes());
        assert_eq!(decode_f32_le(&raw)?, vec![0.0, 0.5]);
        Ok(())
    }

    #[test]
    fn unit_conversion_clamps() {
        assert_eq!(from_unit_f32(&[2.0, -2.0, 0.0]), vec![32_767, -32_767, 0]);
    }
}
