use serde::{Deserialize, Serialize};
use std::net::IpAddr;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum KeyAlgorithm {
    EcdsaP256,
    EcdsaP384,
    Ed25519,
    Rsa2048,
    Rsa4096,
}

impl KeyAlgorithm {
    #[must_use]
    pub fn default_enterprise() -> Self {
        Self::EcdsaP256
    }

    #[must_use]
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::EcdsaP256 => "ecdsa_p256",
            Self::EcdsaP384 => "ecdsa_p384",
            Self::Ed25519 => "ed25519",
            Self::Rsa2048 => "rsa_2048",
            Self::Rsa4096 => "rsa_4096",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CertificateUsage {
    ServerTls,
    ClientAuth,
    DualTls,
    RootCa,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SanKind {
    Dns,
    Ip,
    Uri,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NetworkCategory {
    Loopback,
    LocalLan,
    Tailscale,
    WireguardVpn,
    PublicDomain,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SanItem {
    pub kind: SanKind,
    pub value: String,
    pub category: NetworkCategory,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct InterfaceSnapshot {
    pub name: String,
    pub addresses: Vec<String>,
    pub is_tailscale: bool,
    pub is_vpn: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EnterprisePkiConfig {
    pub organization: String,
    pub common_name: String,
    pub validity_days: u32,
    pub algorithm: KeyAlgorithm,
    pub enable_tailscale: bool,
    pub enable_vpn: bool,
    pub enable_lan: bool,
    pub custom_dns: Vec<String>,
    pub custom_ips: Vec<String>,
}

impl Default for EnterprisePkiConfig {
    fn default() -> Self {
        Self {
            organization: "Nuxiva Enterprise OS".to_string(),
            common_name: "Nuxiva Enterprise Root CA".to_string(),
            validity_days: 397,
            algorithm: KeyAlgorithm::EcdsaP256,
            enable_tailscale: true,
            enable_vpn: true,
            enable_lan: true,
            custom_dns: Vec::new(),
            custom_ips: Vec::new(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PkiPlan {
    pub sans: Vec<SanItem>,
    pub validity_days: u32,
    pub algorithm: KeyAlgorithm,
    pub ca_organization: String,
    pub ca_common_name: String,
    pub has_tailscale: bool,
    pub has_vpn: bool,
    pub warning_messages: Vec<String>,
}

#[must_use]
pub fn classify_network_address(addr: &IpAddr) -> NetworkCategory {
    match addr {
        IpAddr::V4(v4) => {
            let octets = v4.octets();
            if v4.is_loopback() {
                NetworkCategory::Loopback
            } else if octets[0] == 100 && (octets[1] & 0xc0) == 64 {
                NetworkCategory::Tailscale
            } else if octets[0] == 10
                || (octets[0] == 172 && (16..=31).contains(&octets[1]))
                || (octets[0] == 192 && octets[1] == 168)
            {
                NetworkCategory::LocalLan
            } else {
                NetworkCategory::PublicDomain
            }
        }
        IpAddr::V6(v6) => {
            if v6.is_loopback() {
                NetworkCategory::Loopback
            } else {
                let segments = v6.segments();
                if (segments[0] & 0xfe00) == 0xfc00 {
                    if segments[0] == 0xfd7a && segments[1] == 0x115c {
                        NetworkCategory::Tailscale
                    } else {
                        NetworkCategory::LocalLan
                    }
                } else {
                    NetworkCategory::PublicDomain
                }
            }
        }
    }
}

#[must_use]
pub fn sanitize_dns_name(raw: &str) -> Option<String> {
    let trimmed = raw.trim().trim_end_matches('.').to_ascii_lowercase();
    if trimmed.is_empty() || trimmed.len() > 253 {
        return None;
    }
    for label in trimmed.split('.') {
        if label.is_empty() || label.len() > 63 {
            return None;
        }
        if label.starts_with('-') || label.ends_with('-') {
            return None;
        }
        if !label.chars().all(|c| c.is_ascii_alphanumeric() || c == '-') {
            return None;
        }
    }
    Some(trimmed)
}

#[allow(clippy::too_many_lines)]
#[must_use]
pub fn build_pki_plan(
    config: &EnterprisePkiConfig,
    ifaces: &[InterfaceSnapshot],
    extra_names: &[String],
) -> PkiPlan {
    let mut sans = Vec::new();
    let mut has_tailscale = false;
    let mut has_vpn = false;
    let mut warnings = Vec::new();

    let loopback_v4 = "127.0.0.1".to_string();
    sans.push(SanItem {
        kind: SanKind::Ip,
        value: loopback_v4,
        category: NetworkCategory::Loopback,
    });

    let loopback_v6 = "::1".to_string();
    sans.push(SanItem {
        kind: SanKind::Ip,
        value: loopback_v6,
        category: NetworkCategory::Loopback,
    });

    for name in ["localhost", "nuxiva.local", "nuxiva"] {
        sans.push(SanItem {
            kind: SanKind::Dns,
            value: name.to_string(),
            category: NetworkCategory::Loopback,
        });
    }

    for name in extra_names {
        if let Some(valid_name) = sanitize_dns_name(name) {
            if !sans.iter().any(|s| s.value == valid_name) {
                let category = if valid_name.ends_with(".ts.net") {
                    has_tailscale = true;
                    NetworkCategory::Tailscale
                } else {
                    NetworkCategory::LocalLan
                };
                sans.push(SanItem {
                    kind: SanKind::Dns,
                    value: valid_name,
                    category,
                });
            }
        }
    }

    for iface in ifaces {
        let is_ts = iface.is_tailscale || iface.name.starts_with("tailscale");
        let is_vpn_iface =
            iface.is_vpn || iface.name.starts_with("wg") || iface.name.starts_with("tun");

        if is_ts && !config.enable_tailscale {
            continue;
        }
        if is_vpn_iface && !config.enable_vpn {
            continue;
        }
        if !is_ts && !is_vpn_iface && !config.enable_lan {
            continue;
        }

        for addr_str in &iface.addresses {
            if let Ok(ip) = addr_str.parse::<IpAddr>() {
                if ip.is_loopback() || ip.is_unspecified() {
                    continue;
                }
                let mut cat = classify_network_address(&ip);
                if is_ts {
                    cat = NetworkCategory::Tailscale;
                    has_tailscale = true;
                } else if is_vpn_iface {
                    cat = NetworkCategory::WireguardVpn;
                    has_vpn = true;
                }
                let formatted = ip.to_string();
                if !sans.iter().any(|s| s.value == formatted) {
                    sans.push(SanItem {
                        kind: SanKind::Ip,
                        value: formatted,
                        category: cat,
                    });
                }
            }
        }
    }

    for custom_dns in &config.custom_dns {
        if let Some(clean) = sanitize_dns_name(custom_dns) {
            if !sans.iter().any(|s| s.value == clean) {
                let category = if clean.ends_with(".ts.net") {
                    has_tailscale = true;
                    NetworkCategory::Tailscale
                } else {
                    NetworkCategory::PublicDomain
                };
                sans.push(SanItem {
                    kind: SanKind::Dns,
                    value: clean,
                    category,
                });
            }
        } else {
            warnings.push(format!("Invalid custom DNS SAN rejected: {custom_dns}"));
        }
    }

    for custom_ip in &config.custom_ips {
        if let Ok(ip) = custom_ip.trim().parse::<IpAddr>() {
            let formatted = ip.to_string();
            if !sans.iter().any(|s| s.value == formatted) {
                let cat = classify_network_address(&ip);
                sans.push(SanItem {
                    kind: SanKind::Ip,
                    value: formatted,
                    category: cat,
                });
            }
        } else {
            warnings.push(format!("Invalid custom IP SAN rejected: {custom_ip}"));
        }
    }

    PkiPlan {
        sans,
        validity_days: config.validity_days.clamp(30, 825),
        algorithm: config.algorithm,
        ca_organization: config.organization.clone(),
        ca_common_name: config.common_name.clone(),
        has_tailscale,
        has_vpn,
        warning_messages: warnings,
    }
}
