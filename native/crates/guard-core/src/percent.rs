const HEX: &[u8; 16] = b"0123456789ABCDEF";

fn hex_digit(nibble: u8) -> char {
    HEX.get(usize::from(nibble & 0x0f))
        .map_or('0', |b| char::from(*b))
}

#[must_use]
pub fn quote(text: &str, safe: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for byte in text.bytes() {
        let ch = char::from(byte);
        if byte.is_ascii_alphanumeric() || (byte.is_ascii() && safe.contains(ch)) {
            out.push(ch);
        } else {
            out.push('%');
            out.push(hex_digit(byte >> 4));
            out.push(hex_digit(byte));
        }
    }
    out
}

#[must_use]
pub fn latin1(bytes: &[u8]) -> String {
    bytes.iter().map(|b| char::from(*b)).collect()
}
