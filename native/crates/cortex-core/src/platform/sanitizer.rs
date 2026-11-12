use unicode_normalization::UnicodeNormalization;

use super::error::{CortexError, CortexResult};

pub const MAX_UTTERANCE_CHARS: usize = 4000;
pub const MAX_IDENTIFIER_CHARS: usize = 64;
const EXPANSION_BUDGET: usize = 8;

const fn is_invisible_format(character: char) -> bool {
    matches!(
        character,
        '\u{00AD}'
            | '\u{061C}'
            | '\u{180E}'
            | '\u{200B}'..='\u{200F}'
            | '\u{202A}'..='\u{202E}'
            | '\u{2060}'..='\u{2064}'
            | '\u{2066}'..='\u{206F}'
            | '\u{FEFF}'
            | '\u{FFF9}'..='\u{FFFB}'
            | '\u{E0000}'..='\u{E007F}'
    )
}

pub fn sanitize_utterance(input: &str, max_chars: usize) -> CortexResult<String> {
    if input.len() > max_chars.saturating_mul(EXPANSION_BUDGET) {
        return Err(CortexError::InputTooLong);
    }
    if input.contains('\0') {
        return Err(CortexError::ForbiddenCharacters);
    }
    let mut cleaned = String::with_capacity(input.len());
    let mut pending_space = false;
    for character in input.nfkc() {
        if is_invisible_format(character) {
            continue;
        }
        if character.is_whitespace() {
            pending_space = !cleaned.is_empty();
            continue;
        }
        if character.is_control() {
            return Err(CortexError::ForbiddenCharacters);
        }
        if pending_space {
            cleaned.push(' ');
            pending_space = false;
        }
        cleaned.push(character);
    }
    if cleaned.is_empty() {
        return Err(CortexError::EmptyInput);
    }
    if cleaned.chars().count() > max_chars {
        return Err(CortexError::InputTooLong);
    }
    Ok(cleaned)
}

pub fn sanitize_identifier(input: &str) -> CortexResult<String> {
    let cleaned = input.trim();
    if cleaned.is_empty() {
        return Err(CortexError::EmptyInput);
    }
    if cleaned.len() > MAX_IDENTIFIER_CHARS {
        return Err(CortexError::InputTooLong);
    }
    let valid = cleaned
        .chars()
        .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || matches!(c, '_' | '-' | '.'));
    let leading_ok = cleaned
        .chars()
        .next()
        .is_some_and(|c| c.is_ascii_lowercase() || c.is_ascii_digit());
    if valid && leading_ok {
        Ok(cleaned.to_owned())
    } else {
        Err(CortexError::InvalidIdentifier)
    }
}

#[cfg(test)]
mod tests {
    use super::{CortexError, MAX_UTTERANCE_CHARS, sanitize_identifier, sanitize_utterance};

    #[test]
    fn collapses_whitespace_and_normalises_compatibility_forms() {
        assert_eq!(
            sanitize_utterance("  ｓｐｅｇｎｉ \t\n la   luce  ", MAX_UTTERANCE_CHARS),
            Ok("spegni la luce".to_owned())
        );
    }

    #[test]
    fn strips_invisible_and_bidirectional_controls() {
        assert_eq!(
            sanitize_utterance("ac\u{200B}cendi\u{202E} luce", MAX_UTTERANCE_CHARS),
            Ok("accendi luce".to_owned())
        );
    }

    #[test]
    fn rejects_nul_and_control_characters() {
        assert_eq!(
            sanitize_utterance("a\0b", MAX_UTTERANCE_CHARS),
            Err(CortexError::ForbiddenCharacters)
        );
        assert_eq!(
            sanitize_utterance("a\u{0007}b", MAX_UTTERANCE_CHARS),
            Err(CortexError::ForbiddenCharacters)
        );
    }

    #[test]
    fn rejects_empty_and_oversized_input() {
        assert_eq!(
            sanitize_utterance(" \u{200B} ", MAX_UTTERANCE_CHARS),
            Err(CortexError::EmptyInput)
        );
        assert_eq!(
            sanitize_utterance(&"a".repeat(41), 40),
            Err(CortexError::InputTooLong)
        );
        assert_eq!(
            sanitize_utterance(&"a".repeat(1000), 40),
            Err(CortexError::InputTooLong)
        );
    }

    #[test]
    fn identifiers_are_restricted_to_a_safe_alphabet() {
        assert_eq!(
            sanitize_identifier("neuron-01.light_on"),
            Ok("neuron-01.light_on".to_owned())
        );
        assert_eq!(
            sanitize_identifier("../etc"),
            Err(CortexError::InvalidIdentifier)
        );
        assert_eq!(
            sanitize_identifier("Upper"),
            Err(CortexError::InvalidIdentifier)
        );
        assert_eq!(sanitize_identifier(" "), Err(CortexError::EmptyInput));
    }
}
