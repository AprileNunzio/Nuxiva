use crate::error::{PeerError, PeerResult};
use std::net::{IpAddr, SocketAddr};

pub const MAX_ADDRS: usize = 8;
pub const MAX_HOST: usize = 253;

pub fn check_addr(raw: &str) -> PeerResult<()> {
    if let Ok(sock) = raw.parse::<SocketAddr>() {
        let ip = sock.ip();
        let bad = sock.port() == 0
            || ip.is_unspecified()
            || ip.is_multicast()
            || matches!(ip, IpAddr::V4(v4) if v4.is_broadcast());
        return if bad { Err(PeerError::Field) } else { Ok(()) };
    }
    let (host, port) = raw.rsplit_once(':').ok_or(PeerError::Field)?;
    let port: u16 = port.parse().map_err(|_| PeerError::Field)?;
    let label_ok = |l: &str| {
        !l.is_empty()
            && l.len() <= 63
            && !l.starts_with('-')
            && !l.ends_with('-')
            && l.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'-')
    };
    if port == 0 || host.is_empty() || host.len() > MAX_HOST || !host.split('.').all(label_ok) {
        return Err(PeerError::Field);
    }
    Ok(())
}

pub fn check_addrs(addrs: &[String]) -> PeerResult<()> {
    if addrs.is_empty() || addrs.len() > MAX_ADDRS {
        return Err(PeerError::Limit);
    }
    let mut seen = std::collections::BTreeSet::new();
    for addr in addrs {
        check_addr(addr)?;
        if !seen.insert(addr.as_str()) {
            return Err(PeerError::Field);
        }
    }
    Ok(())
}
