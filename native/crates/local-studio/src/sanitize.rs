use crate::error::{StudioError, StudioResult};

pub const MAX_PROMPT_CHARS: usize = 32_768;
const MAX_ID: usize = 128;

fn hidden(c: char) -> bool {
    matches!(c, '\u{200b}'..='\u{200f}' | '\u{202a}'..='\u{202e}' | '\u{2066}'..='\u{2069}' | '\u{feff}')
}

pub fn clean_text(raw: &str, max_chars: usize, field: &'static str) -> StudioResult<String> {
    let cleaned: String = raw
        .chars()
        .filter(|c| (!c.is_control() || matches!(c, '\n' | '\t')) && !hidden(*c))
        .collect();
    let trimmed = cleaned.trim();
    if trimmed.is_empty() {
        return Err(StudioError::Invalid(field));
    }
    if trimmed.chars().count() > max_chars {
        return Err(StudioError::TooLarge);
    }
    Ok(trimmed.to_owned())
}

#[must_use]
pub fn valid_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= MAX_ID
        && !id.contains("..")
        && !id.starts_with(['/', '.', '-'])
        && id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'/' | b'-' | b'_' | b'.' | b':'))
}

pub(crate) fn require_id(id: &str, field: &'static str) -> StudioResult<String> {
    if valid_id(id) {
        Ok(id.to_owned())
    } else {
        Err(StudioError::Invalid(field))
    }
}
