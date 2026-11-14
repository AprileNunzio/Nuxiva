use std::net::IpAddr;
use std::time::Duration;

use futures_util::StreamExt;
use serde::Deserialize;
use tokio::sync::{mpsc, watch};
use tokio_tungstenite::tungstenite::Message;
use tokio_tungstenite::tungstenite::protocol::WebSocketConfig;

use crate::error::{BrainError, BrainResult};
use crate::supervisor::Event;

const MAX_MESSAGE: usize = 256 * 1024;
const MAX_TEXT_BYTES: usize = 8 * 1024;
const BACKOFF_START: Duration = Duration::from_millis(250);
const BACKOFF_CEIL: Duration = Duration::from_secs(10);

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EarEndpoint {
    host: IpAddr,
    port: u16,
}

impl EarEndpoint {
    pub fn loopback(host: &str, port: u16) -> BrainResult<Self> {
        let host: IpAddr = host.parse().map_err(|_| BrainError::Input("ear_host"))?;
        if !host.is_loopback() || port == 0 {
            return Err(BrainError::Input("ear_host"));
        }
        Ok(Self { host, port })
    }

    #[must_use]
    pub fn url(&self) -> String {
        match self.host {
            IpAddr::V4(v4) => format!("ws://{v4}:{}", self.port),
            IpAddr::V6(v6) => format!("ws://[{v6}]:{}", self.port),
        }
    }
}

#[derive(Debug, Deserialize)]
struct Wire {
    #[serde(rename = "type")]
    kind: String,
    #[serde(default)]
    text: String,
    #[serde(default)]
    speaker: Option<String>,
    #[serde(default)]
    speaker_score: f32,
    #[serde(default)]
    voice_known: bool,
}

pub fn parse(raw: &str, at_ms: u64) -> BrainResult<Option<Event>> {
    let wire: Wire = serde_json::from_str(raw).map_err(|_| BrainError::Input("ear_json"))?;
    if wire.kind != "transcript" {
        return Ok(None);
    }
    if wire.text.is_empty()
        || wire.text.len() > MAX_TEXT_BYTES
        || wire.text.chars().any(char::is_control)
    {
        return Err(BrainError::Input("ear_text"));
    }
    let speaker = wire
        .speaker
        .filter(|s| wire.voice_known && nuxiva_ear_core::valid_slug(s));
    let score = if wire.speaker_score.is_finite() {
        wire.speaker_score.clamp(0.0, 1.0)
    } else {
        0.0
    };
    Ok(Some(Event::Heard {
        speaker,
        text: wire.text,
        score,
        at_ms,
    }))
}

fn now_ms() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |d| u64::try_from(d.as_millis()).unwrap_or(u64::MAX))
}

async fn session(endpoint: &EarEndpoint, events: &mpsc::Sender<Event>) -> BrainResult<bool> {
    let config = WebSocketConfig::default()
        .max_message_size(Some(MAX_MESSAGE))
        .max_frame_size(Some(MAX_MESSAGE));
    let (mut stream, _) =
        tokio_tungstenite::connect_async_with_config(endpoint.url(), Some(config), false)
            .await
            .map_err(|_| BrainError::Closed)?;
    while let Some(frame) = stream.next().await {
        let message = frame.map_err(|_| BrainError::Closed)?;
        let Message::Text(raw) = message else {
            continue;
        };
        match parse(raw.as_str(), now_ms()) {
            Ok(Some(event)) => {
                if events.send(event).await.is_err() {
                    return Ok(false);
                }
            }
            Ok(None) => {}
            Err(error) => {
                if events.send(Event::Fault(error)).await.is_err() {
                    return Ok(false);
                }
            }
        }
    }
    Ok(true)
}

pub async fn run(
    endpoint: EarEndpoint,
    events: mpsc::Sender<Event>,
    mut stop: watch::Receiver<bool>,
) {
    let mut delay = BACKOFF_START;
    loop {
        let outcome = tokio::select! {
            biased;
            _ = stop.changed() => return,
            result = session(&endpoint, &events) => result,
        };
        match outcome {
            Ok(false) => return,
            Ok(true) => delay = BACKOFF_START,
            Err(error) => {
                if events.send(Event::Fault(error)).await.is_err() {
                    return;
                }
                delay = delay.saturating_mul(2).min(BACKOFF_CEIL);
            }
        }
        tokio::select! {
            biased;
            _ = stop.changed() => return,
            () = tokio::time::sleep(delay) => {}
        }
    }
}
