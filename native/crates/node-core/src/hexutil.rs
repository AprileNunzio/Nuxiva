use crate::error::{NodeError, NodeResult};

const DIGITS: &[u8; 16] = b"0123456789abcdef";

#[must_use]
pub fn encode(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len().saturating_mul(2));
    for byte in bytes {
        out.push(char::from(
            DIGITS.get(usize::from(byte >> 4)).copied().unwrap_or(b'0'),
        ));
        out.push(char::from(
            DIGITS
                .get(usize::from(byte & 0x0f))
                .copied()
                .unwrap_or(b'0'),
        ));
    }
    out
}

fn nibble(c: u8) -> NodeResult<u8> {
    match c {
        b'0'..=b'9' => Ok(c.saturating_sub(b'0')),
        b'a'..=b'f' => Ok(c.saturating_sub(b'a').saturating_add(10)),
        _ => Err(NodeError::Hex),
    }
}

pub fn decode(raw: &str) -> NodeResult<Vec<u8>> {
    let bytes = raw.as_bytes();
    if bytes.len() % 2 != 0 {
        return Err(NodeError::Hex);
    }
    bytes
        .chunks_exact(2)
        .map(|pair| match pair {
            [high, low] => Ok((nibble(*high)? << 4) | nibble(*low)?),
            _ => Err(NodeError::Hex),
        })
        .collect()
}
