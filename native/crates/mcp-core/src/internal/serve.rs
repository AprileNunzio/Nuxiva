use std::sync::Arc;

use serde_json::{Map, Value, json};
use tokio::sync::{Semaphore, mpsc};

use crate::protocol::{ErrorObject, Id, Implementation, Message, Outcome, Response, negotiate};
use crate::transport::Link;

const METHOD_NOT_FOUND: i64 = -32_601;
const INVALID_PARAMS: i64 = -32_602;
const INTERNAL: i64 = -32_603;
const DEFAULT_VERSION: &str = "2025-06-18";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ToolOutput {
    pub text: String,
    pub is_error: bool,
}

impl ToolOutput {
    #[must_use]
    pub fn ok(text: impl Into<String>) -> Self {
        Self {
            text: text.into(),
            is_error: false,
        }
    }

    #[must_use]
    pub fn fail(text: impl Into<String>) -> Self {
        Self {
            text: text.into(),
            is_error: true,
        }
    }
}

pub trait ToolServer: Send + Sync + 'static {
    fn info(&self) -> Implementation;
    fn tools(&self) -> Vec<Value>;
    fn call(&self, name: &str, arguments: &Map<String, Value>) -> ToolOutput;
}

async fn respond(tx: &mpsc::Sender<Vec<u8>>, id: Id, outcome: Outcome) {
    if let Ok(bytes) = (Message::Response(Response { id, outcome })).to_vec() {
        let _ = tx.send(bytes).await;
    }
}

fn failure(code: i64, message: &str) -> Outcome {
    Outcome::Error(ErrorObject {
        code,
        message: message.to_owned(),
        data: None,
    })
}

fn initialize(server: &dyn ToolServer, params: Option<&Map<String, Value>>) -> Value {
    let requested = params
        .and_then(|p| p.get("protocolVersion"))
        .and_then(Value::as_str)
        .filter(|v| negotiate(v).is_some())
        .unwrap_or(DEFAULT_VERSION);
    json!({
        "protocolVersion": requested,
        "capabilities": {"tools": {"listChanged": false}},
        "serverInfo": server.info(),
    })
}

pub fn serve(server: Arc<dyn ToolServer>, link: Link, max_message: usize, max_in_flight: usize) {
    let Link { tx, mut rx, guard } = link;
    tokio::spawn(async move {
        let _guard = guard;
        let permits = Arc::new(Semaphore::new(max_in_flight.max(1)));
        while let Some(bytes) = rx.recv().await {
            let Ok(Message::Request(request)) = Message::parse(&bytes, max_message) else {
                continue;
            };
            let id = request.id;
            let params = request.params;
            match request.method.as_str() {
                "initialize" => {
                    let result = initialize(server.as_ref(), params.as_ref());
                    respond(&tx, id, Outcome::Result(result)).await;
                }
                "ping" => respond(&tx, id, Outcome::Result(json!({}))).await,
                "tools/list" => {
                    let result = json!({"tools": server.tools()});
                    respond(&tx, id, Outcome::Result(result)).await;
                }
                "tools/call" => {
                    let Some(name) = params
                        .as_ref()
                        .and_then(|p| p.get("name"))
                        .and_then(Value::as_str)
                        .map(str::to_owned)
                    else {
                        respond(&tx, id, failure(INVALID_PARAMS, "name")).await;
                        continue;
                    };
                    let arguments = params
                        .as_ref()
                        .and_then(|p| p.get("arguments"))
                        .and_then(Value::as_object)
                        .cloned()
                        .unwrap_or_default();
                    let (server, tx, permits) =
                        (Arc::clone(&server), tx.clone(), Arc::clone(&permits));
                    tokio::spawn(async move {
                        let Ok(permit) = permits.acquire_owned().await else {
                            return;
                        };
                        let outcome =
                            tokio::task::spawn_blocking(move || server.call(&name, &arguments))
                                .await;
                        drop(permit);
                        let outcome = match outcome {
                            Ok(out) => Outcome::Result(json!({
                                "content": [{"type": "text", "text": out.text}],
                                "isError": out.is_error,
                            })),
                            Err(_) => failure(INTERNAL, "internal"),
                        };
                        respond(&tx, id, outcome).await;
                    });
                }
                _ => respond(&tx, id, failure(METHOD_NOT_FOUND, "method")).await,
            }
        }
    });
}
