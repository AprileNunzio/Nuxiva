use serde_json::{Value, json};

use crate::error::{StudioError, StudioResult};
use crate::sanitize::{MAX_PROMPT_CHARS, clean_text, require_id};

const MAX_MESSAGES: usize = 64;
const MAX_OUTPUT_TOKENS: u32 = 8192;
const MAX_TEMPERATURE_MILLI: u16 = 2000;
const MAX_IMAGES: u8 = 4;
const MAX_SPEECH_CHARS: usize = 4096;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Role {
    System,
    User,
    Assistant,
}

impl Role {
    const fn name(self) -> &'static str {
        match self {
            Self::System => "system",
            Self::User => "user",
            Self::Assistant => "assistant",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Message {
    pub role: Role,
    pub content: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ChatRequest {
    pub model: String,
    pub messages: Vec<Message>,
    pub max_tokens: u32,
    pub temperature_milli: Option<u16>,
    pub thinking: bool,
}

impl ChatRequest {
    pub fn to_json(&self) -> StudioResult<Value> {
        let model = require_id(&self.model, "model")?;
        if self.messages.is_empty() || self.messages.len() > MAX_MESSAGES {
            return Err(StudioError::Invalid("messages"));
        }
        if !(1..=MAX_OUTPUT_TOKENS).contains(&self.max_tokens) {
            return Err(StudioError::Invalid("max_tokens"));
        }
        let mut total = 0_usize;
        let mut messages = Vec::with_capacity(self.messages.len());
        for message in &self.messages {
            let content = clean_text(&message.content, MAX_PROMPT_CHARS, "content")?;
            total = total.saturating_add(content.chars().count());
            messages.push(json!({"role": message.role.name(), "content": content}));
        }
        if total > MAX_PROMPT_CHARS.saturating_mul(2) {
            return Err(StudioError::TooLarge);
        }
        let mut body = json!({
            "model": model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "stream": false,
            "enable_tools": false,
            "enable_thinking": self.thinking,
        });
        if let Some(milli) = self.temperature_milli {
            if milli > MAX_TEMPERATURE_MILLI {
                return Err(StudioError::Invalid("temperature"));
            }
            if let Some(map) = body.as_object_mut() {
                map.insert("temperature".into(), json!(f64::from(milli) / 1000.0));
            }
        }
        Ok(body)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ImageSize {
    Square512,
    Square768,
    Square1024,
    Wide,
    Tall,
}

impl ImageSize {
    const fn spec(self) -> &'static str {
        match self {
            Self::Square512 => "512x512",
            Self::Square768 => "768x768",
            Self::Square1024 => "1024x1024",
            Self::Wide => "1344x768",
            Self::Tall => "768x1344",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ImageRequest {
    pub model: String,
    pub prompt: String,
    pub size: ImageSize,
    pub count: u8,
}

impl ImageRequest {
    pub fn to_json(&self) -> StudioResult<Value> {
        let model = require_id(&self.model, "model")?;
        let prompt = clean_text(&self.prompt, MAX_PROMPT_CHARS, "prompt")?;
        if !(1..=MAX_IMAGES).contains(&self.count) {
            return Err(StudioError::Invalid("count"));
        }
        Ok(json!({
            "model": model,
            "prompt": prompt,
            "size": self.size.spec(),
            "n": self.count,
            "response_format": "b64_json",
        }))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SpeechFormat {
    Wav,
    Mp3,
    Flac,
}

impl SpeechFormat {
    pub(crate) const fn name(self) -> &'static str {
        match self {
            Self::Wav => "wav",
            Self::Mp3 => "mp3",
            Self::Flac => "flac",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SpeechRequest {
    pub model: String,
    pub input: String,
    pub voice: String,
    pub format: SpeechFormat,
}

impl SpeechRequest {
    pub fn to_json(&self) -> StudioResult<Value> {
        Ok(json!({
            "model": require_id(&self.model, "model")?,
            "input": clean_text(&self.input, MAX_SPEECH_CHARS, "input")?,
            "voice": require_id(&self.voice, "voice")?,
            "response_format": self.format.name(),
        }))
    }
}
