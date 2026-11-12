pub const MAX_TOKEN: usize = 32;

#[must_use]
pub fn tokens(text: &str, max: usize) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    for raw in text.split(|c: char| !c.is_alphanumeric()) {
        if raw.is_empty() || out.len() >= max {
            continue;
        }
        let word: String = raw
            .chars()
            .flat_map(char::to_lowercase)
            .take(MAX_TOKEN)
            .collect();
        if !out.contains(&word) {
            out.push(word);
        }
    }
    out
}

#[must_use]
pub fn shard(digest: &str) -> Option<String> {
    if digest.len() != 64
        || !digest
            .bytes()
            .all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f'))
    {
        return None;
    }
    Some(format!(
        "{}/{}/{digest}",
        digest.get(0..2)?,
        digest.get(2..4)?
    ))
}
