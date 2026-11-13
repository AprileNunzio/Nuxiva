use serde_json::{Value, json};
use tokio::sync::mpsc;

use crate::{Id, Link, Message, Outcome, Response};

pub const MAX: usize = 1024 * 1024;

pub fn tool(name: &str) -> Value {
    json!({"name": name, "inputSchema": {"type": "object"}})
}

pub fn reply(request_id: Id, result: Value) -> Vec<u8> {
    Message::Response(Response {
        id: request_id,
        outcome: Outcome::Result(result),
    })
    .to_vec()
    .unwrap_or_default()
}

pub fn answer(method: &str, params: Option<&Value>) -> Option<Value> {
    match method {
        "initialize" => Some(json!({
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {"listChanged": true}},
            "serverInfo": {"name": "fake", "version": "1"}
        })),
        "tools/list" => {
            let cursor = params.and_then(|p| p.get("cursor")).and_then(Value::as_str);
            Some(match cursor {
                None => json!({"tools": [tool("a"), tool("b")], "nextCursor": "p2"}),
                Some("p2") => json!({"tools": [tool("c"), {"name": "bad"}]}),
                Some(_) => json!({"tools": []}),
            })
        }
        "tools/call" => {
            let name = params.and_then(|p| p.get("name")).and_then(Value::as_str)?;
            if name == "silent" {
                return None;
            }
            Some(json!({"content": [{"type": "text", "text": name}]}))
        }
        _ => Some(json!({})),
    }
}

pub fn serve(mut link: Link, seen: mpsc::UnboundedSender<String>) {
    tokio::spawn(async move {
        while let Some(bytes) = link.rx.recv().await {
            let Ok(message) = Message::parse(&bytes, MAX) else {
                continue;
            };
            match message {
                Message::Request(request) => {
                    let params = request.params.map(Value::Object);
                    let _ = seen.send(request.method.clone());
                    if let Some(result) = answer(&request.method, params.as_ref()) {
                        let _ = link.tx.send(reply(request.id, result)).await;
                    }
                }
                Message::Notification(notification) => {
                    let _ = seen.send(notification.method);
                }
                Message::Response(_) => {}
            }
        }
    });
}
