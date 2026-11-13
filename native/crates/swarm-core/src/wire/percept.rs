use serde::{Deserialize, Serialize};

use super::ident::Ident;
use super::{Validate, version};
use crate::error::{SwarmError, SwarmResult};
use crate::settings::Settings;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Channel {
    Voice,
    Text,
    Vision,
    Event,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Affect {
    pub valence: i16,
    pub arousal: u16,
    pub source: Ident,
    pub at_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Percept {
    pub schema_version: u32,
    pub id: Ident,
    pub at_ms: u64,
    pub channel: Channel,
    pub text: String,
    #[serde(default)]
    pub speaker: Option<Ident>,
    #[serde(default)]
    pub addressee_permille: u16,
    #[serde(default)]
    pub emotion: Option<Affect>,
    #[serde(default)]
    pub scene_ref: Option<Ident>,
    #[serde(default)]
    pub audio_ref: Option<Ident>,
    #[serde(default)]
    pub presence: Vec<Ident>,
}

fn clean_text(text: &str) -> bool {
    !text
        .chars()
        .any(|c| c.is_control() && !matches!(c, '\n' | '\t'))
}

impl Validate for Affect {
    fn validate(&self, _settings: &Settings) -> SwarmResult<()> {
        if (-1000..=1000).contains(&self.valence) && self.arousal <= 1000 {
            Ok(())
        } else {
            Err(SwarmError::Invalid)
        }
    }
}

impl Validate for Percept {
    fn validate(&self, settings: &Settings) -> SwarmResult<()> {
        version(self.schema_version)?;
        if self.text.chars().count() > settings.max_text_chars {
            return Err(SwarmError::TooLarge);
        }
        if !clean_text(&self.text) || self.addressee_permille > 1000 {
            return Err(SwarmError::Invalid);
        }
        if self.presence.len() > settings.max_presence {
            return Err(SwarmError::TooLarge);
        }
        if let Some(affect) = &self.emotion {
            affect.validate(settings)?;
        }
        Ok(())
    }
}
