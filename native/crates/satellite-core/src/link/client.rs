use std::time::Duration;

use nuxiva_node_core::DeviceKey;
use serde_json::Value;
use ureq::Agent;
use zeroize::Zeroizing;

use super::tls::pinned_agent;
use crate::vault::Identity;

use super::enroll::now;

const BODY_LIMIT: u64 = 1024 * 1024;

#[derive(Debug, PartialEq, Eq)]
pub enum LinkError {
    Unauthorized,
    Signature(String),
    Rejected(u16, String),
    Network(String),
    Protocol,
    Pin(&'static str),
    InvalidServer,
}

impl LinkError {
    #[must_use]
    pub fn network(error: &ureq::Error) -> Self {
        Self::Network(error.to_string())
    }
}

impl std::fmt::Display for LinkError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Unauthorized => write!(f, "unauthorized"),
            Self::Signature(code) => write!(f, "signature: {code}"),
            Self::Rejected(status, detail) => write!(f, "rejected {status}: {detail}"),
            Self::Network(message) => write!(f, "network: {message}"),
            Self::Protocol => write!(f, "protocol"),
            Self::Pin(reason) => write!(f, "tls_pin: {reason}"),
            Self::InvalidServer => write!(f, "invalid_server"),
        }
    }
}

pub fn normalize_server(raw: &str) -> Result<String, LinkError> {
    let rest = raw
        .trim()
        .trim_end_matches('/')
        .strip_prefix("https://")
        .ok_or(LinkError::InvalidServer)?;
    let valid = !rest.is_empty()
        && rest.len() <= 255
        && rest
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '-' | ':' | '[' | ']'));
    if !valid {
        return Err(LinkError::InvalidServer);
    }
    Ok(format!("https://{}", rest.to_ascii_lowercase()))
}

#[derive(Debug)]
pub struct Link {
    agent: Agent,
    server: String,
    node_id: String,
    token: Zeroizing<String>,
    key: Option<DeviceKey>,
}

impl Link {
    pub fn open(identity: &Identity, timeout: Duration) -> Result<Self, LinkError> {
        let key = if identity.secret.is_empty() {
            None
        } else {
            Some(DeviceKey::from_seed_hex(&identity.secret).map_err(|_| LinkError::Protocol)?)
        };
        Ok(Self {
            agent: pinned_agent(&identity.ca_pem, timeout)?,
            server: normalize_server(&identity.server)?,
            node_id: identity.node_id.clone(),
            token: Zeroizing::new(identity.token.clone()),
            key,
        })
    }

    pub fn anonymous(server: &str, ca_pem: &str, timeout: Duration) -> Result<Self, LinkError> {
        Ok(Self {
            agent: pinned_agent(ca_pem, timeout)?,
            server: normalize_server(server)?,
            node_id: String::new(),
            token: Zeroizing::new(String::new()),
            key: None,
        })
    }

    pub fn proving(
        server: &str,
        ca_pem: &str,
        node_id: &str,
        seed_hex: &str,
        timeout: Duration,
    ) -> Result<Self, LinkError> {
        Ok(Self {
            agent: pinned_agent(ca_pem, timeout)?,
            server: normalize_server(server)?,
            node_id: node_id.to_owned(),
            token: Zeroizing::new(String::new()),
            key: Some(DeviceKey::from_seed_hex(seed_hex).map_err(|_| LinkError::Protocol)?),
        })
    }

    #[must_use]
    pub fn is_signed(&self) -> bool {
        self.key.is_some()
    }

    pub fn post(&self, path: &str, body: &Value) -> Result<Value, LinkError> {
        let payload = serde_json::to_vec(body).map_err(|_| LinkError::Protocol)?;
        let mut request = self
            .agent
            .post(&format!("{}{path}", self.server))
            .header("Content-Type", "application/json");
        if let Some(key) = &self.key {
            let ts = i64::try_from(now()).map_err(|_| LinkError::Protocol)?;
            let proof = key
                .sign(&self.node_id, "POST", path, &payload, ts)
                .map_err(|_| LinkError::Protocol)?;
            request = request
                .header("X-Nuxiva-Node", &self.node_id)
                .header("X-Nuxiva-Ts", &proof.ts.to_string())
                .header("X-Nuxiva-Nonce", &proof.nonce)
                .header("X-Nuxiva-Sig", &proof.signature);
        }
        if !self.token.is_empty() {
            request = request
                .header("X-Nuxiva-Node", &self.node_id)
                .header("Authorization", &format!("Bearer {}", self.token.as_str()));
        }
        let mut response = request
            .send(&payload[..])
            .map_err(|e| LinkError::network(&e))?;
        let status = response.status().as_u16();
        let text = response
            .body_mut()
            .with_config()
            .limit(BODY_LIMIT)
            .read_to_string()
            .map_err(|e| LinkError::network(&e))?;
        let parsed: Value = if text.trim().is_empty() {
            Value::Object(serde_json::Map::new())
        } else {
            serde_json::from_str(&text).map_err(|_| LinkError::Protocol)?
        };
        match status {
            200..=299 => Ok(parsed),
            401 => Err(signature_failure(&parsed)),
            _ => Err(LinkError::Rejected(
                status,
                parsed
                    .get("detail")
                    .and_then(Value::as_str)
                    .unwrap_or_default()
                    .chars()
                    .take(120)
                    .collect(),
            )),
        }
    }
}

pub(crate) fn signature_failure(parsed: &Value) -> LinkError {
    match parsed.get("detail").and_then(Value::as_str) {
        Some(code) if code.starts_with("node.error.") => {
            LinkError::Signature(code.chars().take(64).collect())
        }
        _ => LinkError::Unauthorized,
    }
}
