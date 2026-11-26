use std::net::{IpAddr, Ipv4Addr, Ipv6Addr};

use reqwest::Url;
use reqwest::header::HeaderValue;

use crate::error::{StudioError, StudioResult};

const MAX_URL: usize = 512;
const ALLOWED_PATHS: [&str; 7] = [
    "v1/models",
    "v1/chat/completions",
    "v1/images/generations",
    "v1/audio/speech",
    "v1/embeddings",
    "openapi.json",
    "v1/props",
];

#[derive(Debug, Clone)]
pub struct Endpoint {
    base: Url,
}

fn private_v4(ip: Ipv4Addr) -> bool {
    let [a, b, ..] = ip.octets();
    ip.is_loopback() || ip.is_private() || (a == 100 && (64..=127).contains(&b))
}

fn private_v6(ip: Ipv6Addr) -> bool {
    let first = ip.segments().first().copied().unwrap_or(0);
    ip.is_loopback() || (first & 0xfe00) == 0xfc00
}

fn private_host(url: &Url) -> bool {
    match url.host() {
        Some(url::Host::Ipv4(ip)) => private_v4(ip),
        Some(url::Host::Ipv6(ip)) => private_v6(ip),
        Some(url::Host::Domain(name)) => name.eq_ignore_ascii_case("localhost"),
        None => false,
    }
}

fn unspecified(url: &Url) -> bool {
    match url.host() {
        Some(url::Host::Ipv4(ip)) => IpAddr::V4(ip).is_unspecified() || ip.is_broadcast(),
        Some(url::Host::Ipv6(ip)) => IpAddr::V6(ip).is_unspecified() || ip.is_multicast(),
        _ => false,
    }
}

impl Endpoint {
    pub fn parse(raw: &str) -> StudioResult<Self> {
        let raw = raw.trim();
        if raw.is_empty() || raw.len() > MAX_URL {
            return Err(StudioError::Invalid("endpoint"));
        }
        let url = Url::parse(raw).map_err(|_| StudioError::Invalid("endpoint"))?;
        let clean = url.username().is_empty()
            && url.password().is_none()
            && url.query().is_none()
            && url.fragment().is_none()
            && url.host_str().is_some()
            && !unspecified(&url);
        if !clean {
            return Err(StudioError::Invalid("endpoint"));
        }
        match url.scheme() {
            "https" => {}
            "http" if private_host(&url) => {}
            "http" => return Err(StudioError::Insecure),
            _ => return Err(StudioError::Invalid("endpoint")),
        }
        let mut base = url;
        let trimmed = base
            .path()
            .trim_end_matches('/')
            .trim_end_matches("/v1")
            .to_owned();
        base.set_path(&trimmed);
        Ok(Self { base })
    }

    #[must_use]
    pub fn is_private(&self) -> bool {
        private_host(&self.base)
    }

    pub(crate) fn join(&self, path: &str) -> StudioResult<Url> {
        if !ALLOWED_PATHS.contains(&path) {
            return Err(StudioError::Invalid("path"));
        }
        let mut full = self.base.clone();
        let prefix = full.path().trim_end_matches('/').to_owned();
        full.set_path(&format!("{prefix}/{path}"));
        Ok(full)
    }

    pub(crate) fn bearer(key: &str) -> StudioResult<HeaderValue> {
        let mut value = HeaderValue::from_str(&format!("Bearer {key}"))
            .map_err(|_| StudioError::Invalid("api_key"))?;
        value.set_sensitive(true);
        Ok(value)
    }
}
