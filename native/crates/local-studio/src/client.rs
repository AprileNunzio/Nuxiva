use std::time::Duration;

use reqwest::header::{AUTHORIZATION, CONTENT_TYPE};
use reqwest::redirect::Policy;
use reqwest::{Client, Method, Response};
use serde_json::Value;

use crate::capability::{Capabilities, Capability, MAX_SCHEMA_BYTES};
use crate::endpoint::Endpoint;
use crate::error::{StudioError, StudioResult};
use crate::media::Media;
use crate::reply::{ChatReply, ModelInfo, parse_chat, parse_images, parse_models};
use crate::request::{ChatRequest, ImageRequest, SpeechRequest};
use crate::secret::ApiKey;

const AUDIO_FIELDS: [&str; 3] = ["audio", "b64_json", "data"];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Limits {
    pub timeout: Duration,
    pub connect: Duration,
    pub max_json: usize,
    pub max_media: usize,
}

impl Default for Limits {
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(180),
            connect: Duration::from_secs(5),
            max_json: 8 << 20,
            max_media: 48 << 20,
        }
    }
}

#[derive(Debug)]
pub struct StudioClient {
    http: Client,
    endpoint: Endpoint,
    key: ApiKey,
    limits: Limits,
    capabilities: Capabilities,
}

struct Raw {
    json: bool,
    body: Vec<u8>,
}

fn classify(error: &reqwest::Error) -> StudioError {
    if error.is_timeout() {
        StudioError::Timeout
    } else {
        StudioError::Transport
    }
}

fn check_status(status: u16) -> StudioResult<()> {
    match status {
        200..=299 => Ok(()),
        401 | 403 => Err(StudioError::Auth),
        429 | 503 => Err(StudioError::Busy),
        400..=499 => Err(StudioError::Rejected(status)),
        _ => Err(StudioError::Upstream(status)),
    }
}

async fn collect(mut response: Response, max: usize) -> StudioResult<Vec<u8>> {
    if response
        .content_length()
        .is_some_and(|len| len > max as u64)
    {
        return Err(StudioError::TooLarge);
    }
    let mut body = Vec::new();
    while let Some(chunk) = response.chunk().await.map_err(|e| classify(&e))? {
        if body.len().saturating_add(chunk.len()) > max {
            return Err(StudioError::TooLarge);
        }
        body.extend_from_slice(&chunk);
    }
    Ok(body)
}

fn text(raw: Raw) -> StudioResult<String> {
    if !raw.json {
        return Err(StudioError::Malformed("content_type"));
    }
    String::from_utf8(raw.body).map_err(|_| StudioError::Malformed("utf8"))
}

impl StudioClient {
    pub fn new(endpoint: Endpoint, key: ApiKey, limits: Limits) -> StudioResult<Self> {
        let http = Client::builder()
            .redirect(Policy::none())
            .https_only(!endpoint.is_private())
            .timeout(limits.timeout)
            .connect_timeout(limits.connect)
            .build()
            .map_err(|_| StudioError::Transport)?;
        Ok(Self {
            http,
            endpoint,
            key,
            limits,
            capabilities: Capabilities::none(),
        })
    }

    #[must_use]
    pub const fn capabilities(&self) -> Capabilities {
        self.capabilities
    }

    async fn send(
        &self,
        method: Method,
        path: &str,
        body: Option<&Value>,
        max: usize,
    ) -> StudioResult<Raw> {
        let url = self.endpoint.join(path)?;
        let mut request = self
            .http
            .request(method, url)
            .header(AUTHORIZATION, Endpoint::bearer(self.key.expose())?);
        if let Some(payload) = body {
            let bytes = serde_json::to_vec(payload)?;
            request = request.header(CONTENT_TYPE, "application/json").body(bytes);
        }
        let response = request.send().await.map_err(|e| classify(&e))?;
        check_status(response.status().as_u16())?;
        let json = response
            .headers()
            .get(CONTENT_TYPE)
            .and_then(|v| v.to_str().ok())
            .is_some_and(|v| v.to_ascii_lowercase().starts_with("application/json"));
        let body = collect(response, max).await?;
        Ok(Raw { json, body })
    }

    pub async fn discover(&mut self) -> StudioResult<Capabilities> {
        let found = match self
            .send(Method::GET, "openapi.json", None, MAX_SCHEMA_BYTES)
            .await
        {
            Ok(raw) => Capabilities::from_openapi(&text(raw)?)?,
            Err(StudioError::Rejected(404)) => {
                self.models().await?;
                Capabilities::none().with(Capability::Chat)
            }
            Err(other) => return Err(other),
        };
        self.capabilities = found;
        Ok(found)
    }

    pub async fn models(&self) -> StudioResult<Vec<ModelInfo>> {
        let raw = self
            .send(Method::GET, "v1/models", None, self.limits.max_json)
            .await?;
        parse_models(&text(raw)?)
    }

    pub async fn chat(&self, request: &ChatRequest) -> StudioResult<ChatReply> {
        self.capabilities.require(Capability::Chat)?;
        let body = request.to_json()?;
        let raw = self
            .send(
                Method::POST,
                Capability::Chat.path(),
                Some(&body),
                self.limits.max_json,
            )
            .await?;
        parse_chat(&text(raw)?)
    }

    pub async fn image(&self, request: &ImageRequest) -> StudioResult<Vec<Media>> {
        self.capabilities.require(Capability::Image)?;
        let body = request.to_json()?;
        let budget = self
            .limits
            .max_media
            .saturating_mul(usize::from(request.count))
            .saturating_mul(4)
            / 3;
        let raw = self
            .send(
                Method::POST,
                Capability::Image.path(),
                Some(&body),
                budget.saturating_add(4096),
            )
            .await?;
        parse_images(&text(raw)?, self.limits.max_media)
    }

    pub async fn speech(&self, request: &SpeechRequest) -> StudioResult<Media> {
        self.capabilities.require(Capability::Speech)?;
        let body = request.to_json()?;
        let budget = self.limits.max_media.saturating_mul(4) / 3;
        let raw = self
            .send(
                Method::POST,
                Capability::Speech.path(),
                Some(&body),
                budget.saturating_add(4096),
            )
            .await?;
        let media = if raw.json {
            let parsed: Value = serde_json::from_slice(&raw.body)?;
            let encoded = AUDIO_FIELDS
                .iter()
                .find_map(|field| parsed.get(*field).and_then(Value::as_str))
                .ok_or(StudioError::Malformed("audio"))?;
            Media::from_base64(encoded, self.limits.max_media)?
        } else {
            Media::from_bytes(raw.body, self.limits.max_media)?
        };
        if media.kind.is_audio() {
            Ok(media)
        } else {
            Err(StudioError::Malformed("media"))
        }
    }
}
