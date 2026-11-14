use std::time::Duration;

use reqwest::redirect::Policy;
use reqwest::{Client, Url};
use serde_json::Value;

use crate::error::ClientError;

pub const MAX_BODY: usize = 16 << 20;
const MAX_PATH: usize = 256;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Reply {
    pub status: u16,
    pub body: String,
}

#[derive(Debug, Clone)]
pub struct LlmClient {
    http: Client,
    base: Url,
}

fn base_url(raw: &str) -> Result<Url, ClientError> {
    let url = Url::parse(raw).map_err(|_| ClientError::Url)?;
    let valid = matches!(url.scheme(), "http" | "https")
        && url.host_str().is_some()
        && url.username().is_empty()
        && url.password().is_none()
        && url.query().is_none()
        && url.fragment().is_none();
    if valid {
        Ok(url)
    } else {
        Err(ClientError::Url)
    }
}

fn endpoint(base: &Url, path: &str) -> Result<Url, ClientError> {
    let clean = path.trim_start_matches('/');
    let safe = !path.contains("//")
        && !clean.is_empty()
        && clean.len() <= MAX_PATH
        && clean
            .split('/')
            .all(|part| !part.is_empty() && part != ".." && part != ".")
        && clean
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '/' | '-' | '_' | '.'));
    if !safe {
        return Err(ClientError::Url);
    }
    let mut full = base.clone();
    let prefix = full.path().trim_end_matches('/').to_owned();
    full.set_path(&format!("{prefix}/{clean}"));
    Ok(full)
}

impl LlmClient {
    pub fn new(base: &str, timeout: Duration, connect: Duration) -> Result<Self, ClientError> {
        let http = Client::builder()
            .redirect(Policy::none())
            .timeout(timeout)
            .connect_timeout(connect)
            .build()
            .map_err(|_| ClientError::Build)?;
        Ok(Self {
            http,
            base: base_url(base)?,
        })
    }

    pub async fn post_json(
        &self,
        path: &str,
        body: &Value,
        bearer: Option<&str>,
    ) -> Result<Reply, ClientError> {
        let url = endpoint(&self.base, path)?;
        let mut request = self.http.post(url).json(body);
        if let Some(token) = bearer {
            request = request.bearer_auth(token);
        }
        let mut response = request.send().await.map_err(|error| classify(&error))?;
        let status = response.status().as_u16();
        let mut collected: Vec<u8> = Vec::new();
        while let Some(chunk) = response.chunk().await.map_err(|error| classify(&error))? {
            if collected.len().saturating_add(chunk.len()) > MAX_BODY {
                return Err(ClientError::TooLarge);
            }
            collected.extend_from_slice(&chunk);
        }
        let body = String::from_utf8(collected).map_err(|_| ClientError::Json)?;
        Ok(Reply { status, body })
    }
}

fn classify(error: &reqwest::Error) -> ClientError {
    if error.is_timeout() {
        ClientError::Timeout
    } else {
        ClientError::Transport
    }
}
