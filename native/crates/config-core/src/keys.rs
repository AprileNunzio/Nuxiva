const SECRET_MARKERS: [&str; 9] = [
    "KEY",
    "TOKEN",
    "PASSWORD",
    "PASSWD",
    "SECRET",
    "PASSPHRASE",
    "CREDENTIALS",
    "CREDENTIAL",
    "COOKIE",
];

#[must_use]
pub fn valid_key(key: &str) -> bool {
    let mut bytes = key.bytes();
    bytes.next().is_some_and(|b| b.is_ascii_uppercase())
        && bytes.all(|b| b.is_ascii_uppercase() || b.is_ascii_digit() || b == b'_')
}

fn marker_at_boundary(key: &str, marker: &str) -> bool {
    key.match_indices(marker).any(|(at, _)| {
        let end = at.saturating_add(marker.len());
        key.get(end..)
            .is_some_and(|rest| rest.is_empty() || rest.starts_with('_'))
    })
}

#[must_use]
pub fn is_secret(key: &str, explicit: &[&str]) -> bool {
    explicit.contains(&key) || SECRET_MARKERS.iter().any(|m| marker_at_boundary(key, m))
}
