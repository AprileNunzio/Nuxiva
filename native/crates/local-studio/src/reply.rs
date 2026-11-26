use serde_json::Value;

use crate::error::{StudioError, StudioResult};
use crate::media::Media;
use crate::sanitize::valid_id;

const MAX_MODELS: usize = 512;

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Usage {
    pub prompt_tokens: u32,
    pub completion_tokens: u32,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ChatReply {
    pub text: String,
    pub reasoning: Option<String>,
    pub finish: String,
    pub usage: Usage,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ModelInfo {
    pub id: String,
    pub loaded: Option<bool>,
}

fn printable(raw: &str) -> String {
    raw.chars()
        .filter(|c| !c.is_control() || matches!(c, '\n' | '\t'))
        .collect()
}

fn count(value: Option<&Value>) -> u32 {
    value
        .and_then(Value::as_u64)
        .and_then(|n| u32::try_from(n).ok())
        .unwrap_or(0)
}

pub(crate) fn parse_chat(body: &str) -> StudioResult<ChatReply> {
    let parsed: Value = serde_json::from_str(body)?;
    let choice = parsed
        .get("choices")
        .and_then(Value::as_array)
        .and_then(|list| list.first())
        .ok_or(StudioError::Malformed("choices"))?;
    let message = choice
        .get("message")
        .ok_or(StudioError::Malformed("message"))?;
    let text = message
        .get("content")
        .and_then(Value::as_str)
        .map(printable)
        .unwrap_or_default();
    let reasoning = message
        .get("reasoning_content")
        .and_then(Value::as_str)
        .map(printable)
        .filter(|r| !r.is_empty());
    if text.is_empty() && reasoning.is_none() {
        return Err(StudioError::Malformed("empty"));
    }
    let finish = choice
        .get("finish_reason")
        .and_then(Value::as_str)
        .filter(|f| valid_id(f))
        .unwrap_or("unknown")
        .to_owned();
    let usage = parsed.get("usage");
    Ok(ChatReply {
        text,
        reasoning,
        finish,
        usage: Usage {
            prompt_tokens: count(usage.and_then(|u| u.get("prompt_tokens"))),
            completion_tokens: count(usage.and_then(|u| u.get("completion_tokens"))),
        },
    })
}

pub(crate) fn parse_models(body: &str) -> StudioResult<Vec<ModelInfo>> {
    let parsed: Value = serde_json::from_str(body)?;
    let data = parsed
        .get("data")
        .and_then(Value::as_array)
        .ok_or(StudioError::Malformed("models"))?;
    if data.len() > MAX_MODELS {
        return Err(StudioError::TooLarge);
    }
    Ok(data
        .iter()
        .filter_map(|entry| {
            let id = entry.get("id").and_then(Value::as_str)?;
            valid_id(id).then(|| ModelInfo {
                id: id.to_owned(),
                loaded: entry.get("loaded").and_then(Value::as_bool),
            })
        })
        .collect())
}

pub(crate) fn parse_images(body: &str, max: usize) -> StudioResult<Vec<Media>> {
    let parsed: Value = serde_json::from_str(body)?;
    let data = parsed
        .get("data")
        .and_then(Value::as_array)
        .ok_or(StudioError::Malformed("images"))?;
    let mut images = Vec::with_capacity(data.len());
    for entry in data {
        let encoded = entry
            .get("b64_json")
            .and_then(Value::as_str)
            .ok_or(StudioError::Malformed("b64_json"))?;
        let media = Media::from_base64(encoded, max)?;
        if !media.kind.is_image() {
            return Err(StudioError::Malformed("media"));
        }
        images.push(media);
    }
    if images.is_empty() {
        return Err(StudioError::Malformed("images"));
    }
    Ok(images)
}
