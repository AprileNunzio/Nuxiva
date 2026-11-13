use serde_json::{Map, Value};

use super::jsonrpc::{Id, Message, Notification, Request};
use super::model::Implementation;

fn object(pairs: Vec<(&str, Value)>) -> Map<String, Value> {
    pairs
        .into_iter()
        .map(|(key, value)| (key.to_owned(), value))
        .collect()
}

#[must_use]
pub fn initialize_request(id: Id, protocol_version: &str, client: &Implementation) -> Message {
    let info = serde_json::to_value(client).unwrap_or(Value::Null);
    Message::Request(Request {
        id,
        method: "initialize".into(),
        params: Some(object(vec![
            ("protocolVersion", Value::String(protocol_version.into())),
            ("capabilities", Value::Object(Map::new())),
            ("clientInfo", info),
        ])),
    })
}

#[must_use]
pub fn initialized_notification() -> Message {
    Message::Notification(Notification {
        method: "notifications/initialized".into(),
        params: None,
    })
}

#[must_use]
pub fn ping_request(id: Id) -> Message {
    Message::Request(Request {
        id,
        method: "ping".into(),
        params: None,
    })
}

#[must_use]
pub fn tools_list_request(id: Id, cursor: Option<&str>) -> Message {
    let params = cursor.map(|c| object(vec![("cursor", Value::String(c.into()))]));
    Message::Request(Request {
        id,
        method: "tools/list".into(),
        params,
    })
}

#[must_use]
pub fn tools_call_request(id: Id, name: &str, arguments: Map<String, Value>) -> Message {
    Message::Request(Request {
        id,
        method: "tools/call".into(),
        params: Some(object(vec![
            ("name", Value::String(name.into())),
            ("arguments", Value::Object(arguments)),
        ])),
    })
}

#[must_use]
pub fn cancelled_notification(request_id: &Id, reason: &str) -> Message {
    Message::Notification(Notification {
        method: "notifications/cancelled".into(),
        params: Some(object(vec![
            ("requestId", request_id.to_value()),
            ("reason", Value::String(reason.into())),
        ])),
    })
}
