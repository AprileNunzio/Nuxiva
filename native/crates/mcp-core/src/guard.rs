use std::net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr};

use reqwest::Url;
use serde::{Deserialize, Serialize};

use crate::error::{McpError, McpResult};

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct NetworkPolicy {
    pub allow_loopback: bool,
    pub allow_private: bool,
    pub ports: Vec<u16>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IpClass {
    Public,
    Private,
    Loopback,
    LinkLocal,
    Metadata,
    Reserved,
}

#[derive(Debug, Clone)]
pub struct Target {
    pub url: Url,
    pub host: String,
    pub port: u16,
    pub secure: bool,
}

fn classify_v4(ip: Ipv4Addr) -> IpClass {
    let [a, b, c, d] = ip.octets();
    if matches!(
        (a, b, c, d),
        (169, 254, 169, 254) | (100, 100, 100, 200) | (192, 0, 0, 192)
    ) {
        IpClass::Metadata
    } else if a == 127 {
        IpClass::Loopback
    } else if a == 169 && b == 254 {
        IpClass::LinkLocal
    } else if a == 10
        || (a == 192 && b == 168)
        || (a == 172 && (16..=31).contains(&b))
        || (a == 100 && (64..=127).contains(&b))
    {
        IpClass::Private
    } else if a == 0
        || a >= 224
        || matches!((a, b, c), (192, 0, 0 | 2) | (198, 51, 100) | (203, 0, 113))
        || (a == 198 && (18..=19).contains(&b))
    {
        IpClass::Reserved
    } else {
        IpClass::Public
    }
}

fn classify_v6(ip: Ipv6Addr) -> IpClass {
    if let Some(mapped) = ip.to_ipv4_mapped() {
        return classify_v4(mapped);
    }
    let s = ip.segments();
    let first = s.first().copied().unwrap_or(0);
    let second = s.get(1).copied().unwrap_or(0);
    if ip.is_loopback() {
        IpClass::Loopback
    } else if ip.is_unspecified() || (first & 0xff00) == 0xff00 {
        IpClass::Reserved
    } else if first == 0xfd00 && second == 0x0ec2 {
        IpClass::Metadata
    } else if (first & 0xffc0) == 0xfe80 {
        IpClass::LinkLocal
    } else if (first & 0xfe00) == 0xfc00 {
        IpClass::Private
    } else if first == 0x2001 && second == 0x0db8 {
        IpClass::Reserved
    } else {
        IpClass::Public
    }
}

#[must_use]
pub fn classify_ip(ip: IpAddr) -> IpClass {
    match ip {
        IpAddr::V4(v4) => classify_v4(v4),
        IpAddr::V6(v6) => classify_v6(v6),
    }
}

#[must_use]
pub fn admit(ip: IpAddr, policy: &NetworkPolicy, secure: bool) -> bool {
    match classify_ip(ip) {
        IpClass::Public => secure,
        IpClass::Private => policy.allow_private,
        IpClass::Loopback => policy.allow_loopback,
        IpClass::LinkLocal | IpClass::Metadata | IpClass::Reserved => false,
    }
}

pub fn parse_target(raw: &str) -> McpResult<Target> {
    let url = Url::parse(raw.trim()).map_err(|_| McpError::NetworkDenied)?;
    let secure = match url.scheme() {
        "https" => true,
        "http" => false,
        _ => return Err(McpError::NetworkDenied),
    };
    if !url.username().is_empty() || url.password().is_some() || url.fragment().is_some() {
        return Err(McpError::NetworkDenied);
    }
    let host = url.host_str().ok_or(McpError::NetworkDenied)?.to_owned();
    let port = url.port_or_known_default().ok_or(McpError::NetworkDenied)?;
    Ok(Target {
        url,
        host,
        port,
        secure,
    })
}

pub async fn resolve(target: &Target, policy: &NetworkPolicy) -> McpResult<Vec<SocketAddr>> {
    if !policy.ports.is_empty() && !policy.ports.contains(&target.port) {
        return Err(McpError::NetworkDenied);
    }
    let addresses: Vec<SocketAddr> = tokio::net::lookup_host((target.host.as_str(), target.port))
        .await
        .map_err(|_| McpError::NetworkDenied)?
        .collect();
    if addresses.is_empty()
        || addresses
            .iter()
            .any(|a| !admit(a.ip(), policy, target.secure))
    {
        return Err(McpError::NetworkDenied);
    }
    Ok(addresses)
}
