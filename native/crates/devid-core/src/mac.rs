#[must_use]
pub fn normalize_mac(raw: &str) -> Option<String> {
    let trimmed = raw.trim();
    if trimmed.len() > 32 {
        return None;
    }
    let hex: String = trimmed
        .chars()
        .filter(|c| !matches!(c, ':' | '-' | '.'))
        .collect();
    if hex.len() != 12 || !hex.chars().all(|c| c.is_ascii_hexdigit()) {
        return None;
    }
    let lower = hex.to_ascii_lowercase();
    if lower == "000000000000" || lower == "ffffffffffff" {
        return None;
    }
    let first = u8::from_str_radix(&lower[0..2], 16).ok()?;
    if first & 1 == 1 {
        return None;
    }
    let pairs: Vec<String> = lower
        .as_bytes()
        .chunks(2)
        .map(|pair| String::from_utf8_lossy(pair).into_owned())
        .collect();
    Some(pairs.join(":"))
}

#[must_use]
pub fn randomized(mac: &str) -> bool {
    mac.get(0..2)
        .and_then(|h| u8::from_str_radix(h, 16).ok())
        .is_some_and(|b| b & 2 == 2)
}
