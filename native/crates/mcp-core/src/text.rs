fn hostile(c: char) -> bool {
    matches!(
        c,
        '\u{200B}'..='\u{200F}'
            | '\u{202A}'..='\u{202E}'
            | '\u{2060}'..='\u{2064}'
            | '\u{2066}'..='\u{2069}'
            | '\u{FEFF}'
            | '\u{FFF9}'..='\u{FFFB}'
    ) || (c.is_control() && c != '\n' && c != '\t')
}

#[must_use]
pub fn sanitize_text(input: &str, max_chars: usize) -> String {
    input
        .chars()
        .filter(|c| !hostile(*c))
        .take(max_chars)
        .collect()
}
