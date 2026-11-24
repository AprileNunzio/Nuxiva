use serde_json::{Value, json};

use reason_understand::Request;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Backend {
    Ollama,
    OpenAiCompatible,
}

impl Backend {
    #[must_use]
    pub fn parse(name: &str) -> Option<Self> {
        match name {
            "ollama" => Some(Self::Ollama),
            "openai" => Some(Self::OpenAiCompatible),
            _ => None,
        }
    }

    #[must_use]
    pub fn path(self) -> &'static str {
        match self {
            Self::Ollama => "api/chat",
            Self::OpenAiCompatible => "chat/completions",
        }
    }

    #[must_use]
    pub fn body(self, model: &str, request: &Request) -> Value {
        let user = request.external.as_ref().map_or_else(
            || request.user.clone(),
            |e| format!("{}\n\n{e}", request.user),
        );
        let messages = json!([
            {"role": "system", "content": request.system},
            {"role": "user", "content": user}
        ]);
        match self {
            Self::Ollama => {
                let schema: Value = serde_json::from_str(request.schema).unwrap_or(Value::Null);
                json!({
                    "model": model,
                    "messages": messages,
                    "stream": false,
                    "format": schema,
                    "options": {"temperature": 0}
                })
            }
            Self::OpenAiCompatible => json!({
                "model": model,
                "messages": messages,
                "temperature": 0,
                "response_format": {"type": "json_object"}
            }),
        }
    }

    #[must_use]
    pub fn extract(self, body: &str) -> Option<(String, u64)> {
        let value: Value = serde_json::from_str(body).ok()?;
        match self {
            Self::Ollama => {
                let content = value.pointer("/message/content")?.as_str()?.to_owned();
                let input = value.get("prompt_eval_count").and_then(Value::as_u64);
                let output = value.get("eval_count").and_then(Value::as_u64);
                Some((
                    content,
                    input.unwrap_or(0).saturating_add(output.unwrap_or(0)),
                ))
            }
            Self::OpenAiCompatible => {
                let content = value
                    .pointer("/choices/0/message/content")?
                    .as_str()?
                    .to_owned();
                let total = value
                    .pointer("/usage/total_tokens")
                    .and_then(Value::as_u64)
                    .unwrap_or(0);
                Some((content, total))
            }
        }
    }
}
