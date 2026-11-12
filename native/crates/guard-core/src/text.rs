#[must_use]
pub fn is_py_space(c: char) -> bool {
    c.is_whitespace() || matches!(c, '\u{1c}'..='\u{1f}')
}

#[must_use]
pub fn py_strip(text: &str) -> &str {
    text.trim_matches(is_py_space)
}

#[must_use]
pub fn is_line_break(c: char) -> bool {
    matches!(
        c,
        '\n' | '\r'
            | '\u{0b}'
            | '\u{0c}'
            | '\u{1c}'
            | '\u{1d}'
            | '\u{1e}'
            | '\u{85}'
            | '\u{2028}'
            | '\u{2029}'
    )
}

#[must_use]
pub fn split_lines(text: &str) -> Vec<&str> {
    let mut lines = Vec::new();
    let mut rest = text;
    while !rest.is_empty() {
        match rest.char_indices().find(|(_, c)| is_line_break(*c)) {
            None => {
                lines.push(rest);
                break;
            }
            Some((at, c)) => {
                let (line, tail) = rest.split_at(at);
                lines.push(line);
                let skip = if tail.starts_with("\r\n") {
                    2
                } else {
                    c.len_utf8()
                };
                rest = tail.get(skip..).unwrap_or_default();
            }
        }
    }
    lines
}
