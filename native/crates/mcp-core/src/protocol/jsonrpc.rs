use serde_json::{Map, Value};

use crate::error::{McpError, McpResult};
use crate::limits::Ceilings;
use crate::text::sanitize_text;

pub const VERSION: &str = "2.0";

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Id {
    Number(i64),
    Text(String),
}

impl Id {
    fn from_value(value: &Value) -> McpResult<Self> {
        match value {
            Value::Number(n) => n.as_i64().map(Self::Number).ok_or(McpError::InvalidMessage),
            Value::String(s) if !s.is_empty() && s.len() <= Ceilings::ID_TEXT => {
                Ok(Self::Text(s.clone()))
            }
            _ => Err(McpError::InvalidMessage),
        }
    }

    #[must_use]
    pub fn to_value(&self) -> Value {
        match self {
            Self::Number(n) => Value::from(*n),
            Self::Text(s) => Value::String(s.clone()),
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct Request {
    pub id: Id,
    pub method: String,
    pub params: Option<Map<String, Value>>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Notification {
    pub method: String,
    pub params: Option<Map<String, Value>>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ErrorObject {
    pub code: i64,
    pub message: String,
    pub data: Option<Value>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Outcome {
    Result(Value),
    Error(ErrorObject),
}

#[derive(Debug, Clone, PartialEq)]
pub struct Response {
    pub id: Id,
    pub outcome: Outcome,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Message {
    Request(Request),
    Notification(Notification),
    Response(Response),
}

fn method_of(value: Value) -> McpResult<String> {
    match value {
        Value::String(s)
            if !s.is_empty()
                && s.len() <= Ceilings::METHOD_LEN
                && s.chars()
                    .all(|c| c.is_ascii_alphanumeric() || matches!(c, '_' | '/' | '.' | '-')) =>
        {
            Ok(s)
        }
        _ => Err(McpError::InvalidMessage),
    }
}

fn params_of(value: Option<Value>) -> McpResult<Option<Map<String, Value>>> {
    match value {
        None => Ok(None),
        Some(Value::Object(map)) => Ok(Some(map)),
        Some(_) => Err(McpError::InvalidMessage),
    }
}

fn error_of(value: Value) -> McpResult<ErrorObject> {
    let Value::Object(mut map) = value else {
        return Err(McpError::InvalidMessage);
    };
    let code = map
        .remove("code")
        .and_then(|v| v.as_i64())
        .ok_or(McpError::InvalidMessage)?;
    let message = match map.remove("message") {
        Some(Value::String(s)) => sanitize_text(&s, Ceilings::ERROR_MESSAGE_CHARS),
        _ => return Err(McpError::InvalidMessage),
    };
    Ok(ErrorObject {
        code,
        message,
        data: map.remove("data"),
    })
}

impl Message {
    pub fn parse(bytes: &[u8], max_bytes: usize) -> McpResult<Self> {
        if bytes.len() > max_bytes {
            return Err(McpError::TooLarge);
        }
        let value: Value = serde_json::from_slice(bytes).map_err(|_| McpError::Parse)?;
        Self::from_value(value)
    }

    pub fn from_value(value: Value) -> McpResult<Self> {
        let Value::Object(mut map) = value else {
            return Err(McpError::InvalidMessage);
        };
        if map.get("jsonrpc").and_then(Value::as_str) != Some(VERSION) {
            return Err(McpError::InvalidMessage);
        }
        let id = map.remove("id");
        let method = map.remove("method");
        match (method, id) {
            (Some(method), Some(id)) => Ok(Self::Request(Request {
                id: Id::from_value(&id)?,
                method: method_of(method)?,
                params: params_of(map.remove("params"))?,
            })),
            (Some(method), None) => Ok(Self::Notification(Notification {
                method: method_of(method)?,
                params: params_of(map.remove("params"))?,
            })),
            (None, Some(id)) => {
                let id = Id::from_value(&id)?;
                let outcome = match (map.remove("result"), map.remove("error")) {
                    (Some(result), None) => Outcome::Result(result),
                    (None, Some(error)) => Outcome::Error(error_of(error)?),
                    _ => return Err(McpError::InvalidMessage),
                };
                Ok(Self::Response(Response { id, outcome }))
            }
            (None, None) => Err(McpError::InvalidMessage),
        }
    }

    #[must_use]
    pub fn to_value(&self) -> Value {
        let mut map = Map::new();
        map.insert("jsonrpc".into(), Value::String(VERSION.into()));
        match self {
            Self::Request(r) => {
                map.insert("id".into(), r.id.to_value());
                map.insert("method".into(), Value::String(r.method.clone()));
                if let Some(p) = &r.params {
                    map.insert("params".into(), Value::Object(p.clone()));
                }
            }
            Self::Notification(n) => {
                map.insert("method".into(), Value::String(n.method.clone()));
                if let Some(p) = &n.params {
                    map.insert("params".into(), Value::Object(p.clone()));
                }
            }
            Self::Response(r) => {
                map.insert("id".into(), r.id.to_value());
                match &r.outcome {
                    Outcome::Result(v) => {
                        map.insert("result".into(), v.clone());
                    }
                    Outcome::Error(e) => {
                        let mut error = Map::new();
                        error.insert("code".into(), Value::from(e.code));
                        error.insert("message".into(), Value::String(e.message.clone()));
                        if let Some(d) = &e.data {
                            error.insert("data".into(), d.clone());
                        }
                        map.insert("error".into(), Value::Object(error));
                    }
                }
            }
        }
        Value::Object(map)
    }

    pub fn to_vec(&self) -> McpResult<Vec<u8>> {
        serde_json::to_vec(&self.to_value()).map_err(|_| McpError::Serialize)
    }
}
