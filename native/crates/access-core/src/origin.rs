use std::net::{IpAddr, Ipv6Addr};

pub const MAX_LOCAL_ADDRESSES: usize = 512;
const MAX_HOST_LEN: usize = 255;

fn unmapped(ip: IpAddr) -> IpAddr {
    match ip {
        IpAddr::V6(v6) => v6.to_ipv4_mapped().map_or(IpAddr::V6(v6), IpAddr::V4),
        v4 @ IpAddr::V4(_) => v4,
    }
}

fn strip_scope(raw: &str) -> &str {
    raw.split_once('%').map_or(raw, |(address, _)| address)
}

#[must_use]
pub fn parse_address(raw: &str) -> Option<IpAddr> {
    let trimmed = strip_scope(raw.trim());
    if trimmed.is_empty() || trimmed.len() > MAX_HOST_LEN {
        return None;
    }
    trimmed.parse::<IpAddr>().ok().map(unmapped)
}

fn usable(ip: IpAddr) -> bool {
    !ip.is_unspecified() && !ip.is_multicast()
}

fn is_own(ip: IpAddr, locals: &[IpAddr]) -> bool {
    usable(ip) && (ip.is_loopback() || locals.contains(&ip))
}

fn host_name(header: &str) -> Option<&str> {
    let value = header.trim();
    if value.is_empty() || value.len() > MAX_HOST_LEN || value.chars().any(char::is_control) {
        return None;
    }
    if let Some(rest) = value.strip_prefix('[') {
        return rest.split_once(']').map(|(inside, _)| inside);
    }
    if value.parse::<Ipv6Addr>().is_ok() {
        return Some(value);
    }
    Some(value.rsplit_once(':').map_or(value, |(name, _)| name))
}

#[must_use]
pub fn normalized_locals(raw: &[String]) -> Vec<IpAddr> {
    raw.iter()
        .take(MAX_LOCAL_ADDRESSES)
        .filter_map(|item| parse_address(item))
        .filter(|ip| usable(*ip))
        .collect()
}

#[must_use]
pub fn is_host_origin(peer: &str, host_header: &str, locals: &[IpAddr]) -> bool {
    let peer_ok = peer.trim().eq_ignore_ascii_case("localhost")
        || parse_address(peer).is_some_and(|ip| is_own(ip, locals));
    if !peer_ok {
        return false;
    }
    let Some(name) = host_name(host_header) else {
        return false;
    };
    let name = name.trim_end_matches('.');
    if name.eq_ignore_ascii_case("localhost") {
        return true;
    }
    parse_address(name).is_some_and(|ip| is_own(ip, locals))
}
