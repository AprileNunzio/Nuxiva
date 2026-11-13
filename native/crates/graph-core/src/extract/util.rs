#[must_use]
pub fn ident(text: &str) -> &str {
    let end = text
        .char_indices()
        .find(|(_, c)| !(c.is_alphanumeric() || *c == '_' || *c == '$'))
        .map_or(text.len(), |(i, _)| i);
    text.get(..end).unwrap_or("")
}

#[must_use]
pub fn after<'a>(line: &'a str, keyword: &str) -> Option<&'a str> {
    let rest = line.strip_prefix(keyword)?;
    if rest.starts_with(char::is_whitespace) {
        Some(rest.trim_start())
    } else {
        None
    }
}

#[must_use]
pub fn strip_all<'a>(mut line: &'a str, words: &[&str]) -> &'a str {
    loop {
        let mut changed = false;
        for word in words {
            if let Some(rest) = after(line, word) {
                line = rest;
                changed = true;
            }
        }
        if !changed {
            return line;
        }
    }
}

#[must_use]
pub fn quoted(text: &str) -> Option<&str> {
    let text = text.trim_start();
    let quote = text
        .chars()
        .next()
        .filter(|c| matches!(c, '\'' | '"' | '`'))?;
    let inner = text.get(quote.len_utf8()..)?;
    let end = inner.find(quote)?;
    inner.get(..end)
}

#[must_use]
pub fn clip(text: &str, max_chars: usize) -> String {
    text.chars()
        .filter(|c| !c.is_control())
        .take(max_chars)
        .collect()
}

#[must_use]
pub fn line_no(index: usize) -> u32 {
    u32::try_from(index.saturating_add(1)).unwrap_or(u32::MAX)
}
