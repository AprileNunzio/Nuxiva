use serde::{Deserialize, Serialize};

use crate::error::{DuplexError, DuplexResult};
use crate::session::Interruption;

const CATALOG: &str = include_str!("intents.json");
pub const MAX_SPOKEN_CHARS: usize = 4_096;
const TAIL_WORDS: usize = 2;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Intent {
    Cancel,
    Continue,
    Modify,
    Replace,
    Unrelated,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct InterruptedReply {
    pub spoken_text: String,
    pub unspoken_ref: Option<String>,
    pub interrupted_at_ms: u64,
    pub spoken_chars: u32,
}

impl InterruptedReply {
    pub fn new(
        note: &Interruption,
        spoken_text: &str,
        unspoken_ref: Option<String>,
    ) -> DuplexResult<Self> {
        if unspoken_ref.as_ref().is_some_and(|r| {
            r.len() > 128
                || !r
                    .chars()
                    .all(|c| c.is_ascii_alphanumeric() || "._:-".contains(c))
        }) {
            return Err(DuplexError::Invalid);
        }
        Ok(Self {
            spoken_text: spoken_text.chars().take(MAX_SPOKEN_CHARS).collect(),
            unspoken_ref,
            interrupted_at_ms: note.at_ms,
            spoken_chars: note.spoken_chars,
        })
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Plan {
    pub intent: Intent,
    pub drop_previous: bool,
    pub resume_ref: Option<String>,
    pub regenerate_ref: Option<String>,
}

#[derive(Debug, Deserialize)]
struct CatalogFile {
    cancel: Vec<String>,
    r#continue: Vec<String>,
    modify: Vec<String>,
}

#[derive(Debug)]
pub struct IntentCatalog {
    cancel: Vec<Vec<String>>,
    resume: Vec<Vec<String>>,
    modify: Vec<Vec<String>>,
}

#[must_use]
pub fn words(text: &str) -> Vec<String> {
    text.split_whitespace()
        .map(|w| {
            w.trim_matches(|c: char| !c.is_alphanumeric())
                .replace(['’', '`'], "'")
                .to_lowercase()
        })
        .filter(|w| !w.is_empty())
        .collect()
}

fn phrases(list: &[String]) -> DuplexResult<Vec<Vec<String>>> {
    if list.is_empty() || list.len() > 128 {
        return Err(DuplexError::Invalid);
    }
    let out: Vec<Vec<String>> = list.iter().map(|p| words(p)).collect();
    if out.iter().any(Vec::is_empty) {
        return Err(DuplexError::Invalid);
    }
    Ok(out)
}

fn starts_with(sentence: &[String], phrase: &[String]) -> bool {
    sentence.get(..phrase.len()) == Some(phrase)
}

fn contains(sentence: &[String], phrase: &[String]) -> bool {
    sentence.windows(phrase.len()).any(|w| w == phrase)
}

impl IntentCatalog {
    pub fn builtin() -> DuplexResult<Self> {
        Self::from_json(CATALOG)
    }

    pub fn from_json(text: &str) -> DuplexResult<Self> {
        if text.len() > 16_384 {
            return Err(DuplexError::TooLarge);
        }
        let file: CatalogFile = serde_json::from_str(text).map_err(|_| DuplexError::Parse)?;
        Ok(Self {
            cancel: phrases(&file.cancel)?,
            resume: phrases(&file.r#continue)?,
            modify: phrases(&file.modify)?,
        })
    }

    #[must_use]
    pub fn classify(&self, text: &str) -> Intent {
        let sentence = words(text);
        if sentence.is_empty() {
            return Intent::Unrelated;
        }
        if self.modify.iter().any(|p| contains(&sentence, p)) {
            return Intent::Modify;
        }
        if let Some(head) = self.resume.iter().find(|p| starts_with(&sentence, p)) {
            let rest = sentence.len().saturating_sub(head.len());
            return if rest <= TAIL_WORDS {
                Intent::Continue
            } else {
                Intent::Unrelated
            };
        }
        if let Some(head) = self.cancel.iter().find(|p| starts_with(&sentence, p)) {
            let rest = sentence.len().saturating_sub(head.len());
            return if rest <= TAIL_WORDS {
                Intent::Cancel
            } else {
                Intent::Replace
            };
        }
        Intent::Unrelated
    }

    #[must_use]
    pub fn plan(&self, interrupted: &InterruptedReply, text: &str) -> Plan {
        let intent = self.classify(text);
        let reference = interrupted.unspoken_ref.clone();
        Plan {
            intent,
            drop_previous: matches!(intent, Intent::Cancel | Intent::Replace),
            resume_ref: if intent == Intent::Continue {
                reference.clone()
            } else {
                None
            },
            regenerate_ref: if intent == Intent::Modify {
                reference
            } else {
                None
            },
        }
    }
}
