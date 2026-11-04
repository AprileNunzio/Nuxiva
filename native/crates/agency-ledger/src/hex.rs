const DIGITS: &[u8; 16] = b"0123456789abcdef";

pub fn encode(bytes: &[u8; 32]) -> String {
    let mut out = String::with_capacity(64);
    for byte in bytes {
        for nibble in [byte >> 4, byte & 0x0f] {
            if let Some(c) = DIGITS.get(usize::from(nibble)) {
                out.push(char::from(*c));
            }
        }
    }
    out
}

pub fn decode(text: &str) -> Option<[u8; 32]> {
    let raw = text.as_bytes();
    if raw.len() != 64 {
        return None;
    }
    let mut out = [0u8; 32];
    for (slot, pair) in out.iter_mut().zip(raw.chunks_exact(2)) {
        let high = value(*pair.first()?)?;
        let low = value(*pair.get(1)?)?;
        *slot = (high << 4) | low;
    }
    Some(out)
}

fn value(c: u8) -> Option<u8> {
    match c {
        b'0'..=b'9' => c.checked_sub(b'0'),
        b'a'..=b'f' => c.checked_sub(b'a').and_then(|v| v.checked_add(10)),
        _ => None,
    }
}
