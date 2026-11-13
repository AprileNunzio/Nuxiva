use std::sync::Arc;
use std::time::Duration;

use reqwest::header::{HeaderMap, HeaderName, HeaderValue};
use reqwest::redirect::Policy;
use serde_json::{Value, json};
use tokio::sync::{Mutex, mpsc};

use super::link::{Link, QUEUE};
use super::sse::SseParser;
use crate::error::{McpError, McpResult};
use crate::protocol::Message;

#[derive(Debug, Clone)]
pub struct HttpConfig {
    pub url: String,
    pub headers: Vec<(String, String)>,
    pub timeout: Duration,
    pub protocol_version: Option<String>,
}

struct Shared {
    client: reqwest::Client,
    url: String,
    headers: HeaderMap,
    protocol_version: Option<String>,
    session: Mutex<Option<String>>,
    max_message: usize,
    inbound: mpsc::Sender<Vec<u8>>,
}

fn header_map(pairs: &[(String, String)]) -> McpResult<HeaderMap> {
    let mut map = HeaderMap::new();
    for (name, value) in pairs {
        let name =
            HeaderName::from_bytes(name.as_bytes()).map_err(|_| McpError::InvalidSettings)?;
        let mut value = HeaderValue::from_str(value).map_err(|_| McpError::InvalidSettings)?;
        value.set_sensitive(true);
        map.insert(name, value);
    }
    Ok(map)
}

pub fn spawn_http(config: &HttpConfig, max_message: usize) -> McpResult<Link> {
    let client = reqwest::Client::builder()
        .redirect(Policy::none())
        .timeout(config.timeout)
        .build()
        .map_err(|_| McpError::Io)?;
    let (out_tx, mut out_rx) = mpsc::channel::<Vec<u8>>(QUEUE);
    let (in_tx, in_rx) = mpsc::channel::<Vec<u8>>(QUEUE);
    let shared = Arc::new(Shared {
        client,
        url: config.url.clone(),
        headers: header_map(&config.headers)?,
        protocol_version: config.protocol_version.clone(),
        session: Mutex::new(None),
        max_message,
        inbound: in_tx,
    });
    tokio::spawn(async move {
        while let Some(bytes) = out_rx.recv().await {
            let shared = Arc::clone(&shared);
            tokio::spawn(async move { exchange(&shared, bytes).await });
        }
    });
    Ok(Link::new(out_tx, in_rx))
}

fn request_id(bytes: &[u8]) -> Option<Value> {
    match Message::parse(bytes, usize::MAX).ok()? {
        Message::Request(request) => Some(request.id.to_value()),
        _ => None,
    }
}

async fn exchange(shared: &Shared, bytes: Vec<u8>) {
    let id = request_id(&bytes);
    let delivered = post(shared, bytes).await.unwrap_or(false);
    if delivered {
        return;
    }
    if let Some(id) = id {
        let error =
            json!({"jsonrpc":"2.0","id":id,"error":{"code":-32000,"message":"transport error"}});
        if let Ok(body) = serde_json::to_vec(&error) {
            let _ = shared.inbound.send(body).await;
        }
    }
}

async fn post(shared: &Shared, bytes: Vec<u8>) -> McpResult<bool> {
    let mut request = shared
        .client
        .post(&shared.url)
        .headers(shared.headers.clone())
        .header("content-type", "application/json")
        .header("accept", "application/json, text/event-stream");
    if let Some(version) = &shared.protocol_version {
        request = request.header("mcp-protocol-version", version);
    }
    if let Some(session) = shared.session.lock().await.clone() {
        request = request.header("mcp-session-id", session);
    }
    let mut response = request.body(bytes).send().await.map_err(|_| McpError::Io)?;
    if let Some(session) = response
        .headers()
        .get("mcp-session-id")
        .and_then(|v| v.to_str().ok())
    {
        *shared.session.lock().await = Some(session.to_owned());
    }
    let status = response.status();
    if status == reqwest::StatusCode::ACCEPTED {
        return Ok(true);
    }
    if !status.is_success() {
        return Err(McpError::Io);
    }
    let streaming = response
        .headers()
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .is_some_and(|v| v.starts_with("text/event-stream"));
    let mut parser = SseParser::new(shared.max_message);
    let mut body: Vec<u8> = Vec::new();
    let mut delivered = false;
    while let Some(chunk) = response.chunk().await.map_err(|_| McpError::Io)? {
        if streaming {
            for event in parser.feed(&chunk)? {
                delivered = true;
                shared
                    .inbound
                    .send(event)
                    .await
                    .map_err(|_| McpError::Closed)?;
            }
        } else {
            body.extend_from_slice(&chunk);
            if body.len() > shared.max_message {
                return Err(McpError::TooLarge);
            }
        }
    }
    if !streaming && !body.is_empty() {
        shared
            .inbound
            .send(body)
            .await
            .map_err(|_| McpError::Closed)?;
        delivered = true;
    }
    Ok(delivered)
}
