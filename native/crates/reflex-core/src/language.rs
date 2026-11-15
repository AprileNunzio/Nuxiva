#![forbid(unsafe_code)]

use nuxiva_langid::detect;

#[derive(Debug, Clone, PartialEq)]
pub struct LanguageDetection {
    pub lang_code: String,
    pub confidence: f64,
    pub reliable: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct LanguageIdentifier;

impl LanguageIdentifier {
    pub const DEFAULT_FALLBACK: &'static str = "it";

    #[must_use]
    pub fn identify(text: &str) -> LanguageDetection {
        let trimmed = text.trim();
        if trimmed.is_empty() {
            return LanguageDetection {
                lang_code: Self::DEFAULT_FALLBACK.to_owned(),
                confidence: 0.0,
                reliable: false,
            };
        }

        if let Some(guess) = detect(trimmed, &[]) {
            LanguageDetection {
                lang_code: guess.code.to_owned(),
                confidence: guess.confidence,
                reliable: guess.reliable,
            }
        } else {
            LanguageDetection {
                lang_code: Self::DEFAULT_FALLBACK.to_owned(),
                confidence: 0.5,
                reliable: false,
            }
        }
    }
}
