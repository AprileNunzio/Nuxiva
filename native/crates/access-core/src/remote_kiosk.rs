use crate::origin::parse_address;
use serde::{Deserialize, Serialize};
use std::net::IpAddr;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum KioskScheme {
    Http,
    Https,
}

impl KioskScheme {
    #[must_use]
    pub fn parse(raw: &str) -> Option<Self> {
        let cleaned = raw.trim();
        if cleaned.eq_ignore_ascii_case("http") {
            Some(Self::Http)
        } else if cleaned.eq_ignore_ascii_case("https") {
            Some(Self::Https)
        } else {
            None
        }
    }

    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Http => "http",
            Self::Https => "https",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RemoteKioskConfig {
    pub enabled: bool,
    pub allow_http: bool,
    pub require_private_network: bool,
}

impl Default for RemoteKioskConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            allow_http: true,
            require_private_network: true,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MediaCapabilities {
    pub camera_preview: bool,
    pub camera_probe: bool,
    pub microphone: bool,
}

impl MediaCapabilities {
    #[must_use]
    pub const fn none() -> Self {
        Self {
            camera_preview: false,
            camera_probe: false,
            microphone: false,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RemoteKioskVerdict {
    pub allowed: bool,
    pub reason: String,
    pub media: MediaCapabilities,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClientContext<'a> {
    pub peer: &'a str,
    pub scheme: &'a str,
    pub host: &'a str,
    pub is_admin: bool,
}

fn is_private_ip(ip: IpAddr) -> bool {
    match ip {
        IpAddr::V4(v4) => v4.is_loopback() || v4.is_private() || v4.is_link_local(),
        IpAddr::V6(v6) => {
            if let Some(mapped) = v6.to_ipv4_mapped() {
                mapped.is_loopback() || mapped.is_private() || mapped.is_link_local()
            } else {
                v6.is_loopback() || v6.is_unicast_link_local()
            }
        }
    }
}

fn valid_host(header: &str) -> bool {
    let trimmed = header.trim();
    if trimmed.is_empty() || trimmed.len() > 255 || trimmed.chars().any(char::is_control) {
        return false;
    }
    !trimmed.contains('/') && !trimmed.contains('\\') && !trimmed.contains('@')
}

#[must_use]
pub fn evaluate_remote_kiosk(
    config: &RemoteKioskConfig,
    ctx: &ClientContext,
) -> RemoteKioskVerdict {
    let Some(scheme) = KioskScheme::parse(ctx.scheme) else {
        return RemoteKioskVerdict {
            allowed: false,
            reason: "remote_kiosk.scheme.invalid".into(),
            media: MediaCapabilities::none(),
        };
    };

    if !valid_host(ctx.host) {
        return RemoteKioskVerdict {
            allowed: false,
            reason: "remote_kiosk.host.invalid".into(),
            media: MediaCapabilities::none(),
        };
    }

    let Some(ip) = parse_address(ctx.peer) else {
        return RemoteKioskVerdict {
            allowed: false,
            reason: "remote_kiosk.peer.invalid".into(),
            media: MediaCapabilities::none(),
        };
    };

    if config.require_private_network && !is_private_ip(ip) {
        return RemoteKioskVerdict {
            allowed: false,
            reason: "remote_kiosk.network.not_private".into(),
            media: MediaCapabilities::none(),
        };
    }

    if !config.enabled {
        return RemoteKioskVerdict {
            allowed: false,
            reason: "remote_kiosk.disabled".into(),
            media: MediaCapabilities::none(),
        };
    }

    if scheme == KioskScheme::Http && !config.allow_http {
        return RemoteKioskVerdict {
            allowed: false,
            reason: "remote_kiosk.http.disallowed".into(),
            media: MediaCapabilities::none(),
        };
    }

    RemoteKioskVerdict {
        allowed: true,
        reason: "remote_kiosk.authorized".into(),
        media: MediaCapabilities {
            camera_preview: true,
            camera_probe: ctx.is_admin,
            microphone: true,
        },
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct KioskAdvisory {
    pub acknowledged: bool,
    pub remote_enabled: bool,
    pub version: String,
}

impl KioskAdvisory {
    #[must_use]
    pub fn new(version: impl Into<String>) -> Self {
        Self {
            acknowledged: false,
            remote_enabled: false,
            version: version.into(),
        }
    }

    pub fn acknowledge(&mut self, enable_remote: bool, version: &str) {
        self.acknowledged = true;
        self.remote_enabled = enable_remote;
        self.version = version.to_string();
    }

    #[must_use]
    pub fn should_prompt(&self, current_version: &str) -> bool {
        !self.acknowledged || self.version != current_version
    }
}
