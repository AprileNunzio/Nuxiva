const SENSITIVE: [&str; 9] = [
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "credential",
];

fn secretish(word: &str) -> bool {
    word.len() >= 32
        && word.bytes().all(|b| {
            b.is_ascii_alphanumeric() || matches!(b, b'+' | b'/' | b'=' | b'_' | b'-' | b'.')
        })
}

fn scrub_line(line: &str) -> String {
    let lower = line.to_lowercase();
    if lower.contains("-----begin") {
        return "[redacted:key]".to_owned();
    }
    if SENSITIVE.iter().any(|k| lower.contains(k)) {
        if let Some(at) = line.find(['=', ':']) {
            let head: String = line.chars().take(line[..at].chars().count()).collect();
            return format!("{head}= [redacted]");
        }
    }
    let mut out = String::with_capacity(line.len());
    let mut word = String::new();
    let flush = |word: &mut String, out: &mut String| {
        if secretish(word) {
            out.push_str("[redacted]");
        } else {
            out.push_str(word);
        }
        word.clear();
    };
    for c in line.chars() {
        if c.is_whitespace() || matches!(c, '"' | '\'' | ',' | ';' | '(' | ')' | '<' | '>') {
            flush(&mut word, &mut out);
            out.push(c);
        } else {
            word.push(c);
        }
    }
    flush(&mut word, &mut out);
    out
}

#[must_use]
pub fn redact(text: &str, max_chars: usize) -> String {
    let mut out = String::new();
    let mut count = 0usize;
    for line in text.lines() {
        let clean: String = line
            .chars()
            .filter(|c| !c.is_control() || *c == '\t')
            .collect();
        let shown = format!("| {}\n", scrub_line(&clean));
        for c in shown.chars() {
            if count >= max_chars {
                return out;
            }
            out.push(c);
            count = count.saturating_add(1);
        }
    }
    out
}

#[must_use]
pub fn normalize_for_fingerprint(text: &str) -> String {
    let mut out = String::new();
    for line in text.lines().take(3) {
        for word in line.split_whitespace() {
            if word.chars().any(|c| c.is_ascii_digit()) {
                out.push('#');
            } else {
                out.push_str(&word.to_lowercase());
            }
            out.push(' ');
        }
        out.push('\n');
    }
    out
}
