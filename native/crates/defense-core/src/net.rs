use std::net::IpAddr;

const LAN4: [(u32, u8); 7] = [
    (0x0A00_0000, 8),
    (0xAC10_0000, 12),
    (0xC0A8_0000, 16),
    (0xA9FE_0000, 16),
    (0x6440_0000, 10),
    (0x7F00_0000, 8),
    (0x0000_0000, 8),
];
const LAN6: [(u128, u8); 4] = [
    (1, 128),
    (0xFC00_u128 << 112, 7),
    (0xFE80_u128 << 112, 10),
    (0, 128),
];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Addr {
    V4(u32),
    V6(u128),
    Mac([u8; 6]),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Net {
    pub base: Addr,
    pub prefix: u8,
}

#[must_use]
pub fn ip(raw: &str) -> Option<Addr> {
    let parsed: IpAddr = raw.trim().parse().ok()?;
    Some(match parsed {
        IpAddr::V4(v4) => Addr::V4(u32::from(v4)),
        IpAddr::V6(v6) => match v6.to_ipv4_mapped() {
            Some(v4) => Addr::V4(u32::from(v4)),
            None => Addr::V6(u128::from(v6)),
        },
    })
}

#[must_use]
pub fn mac(raw: &str) -> Option<[u8; 6]> {
    let text = raw.trim().to_ascii_lowercase().replace('-', ":");
    let parts: Vec<&str> = text.split(':').collect();
    if parts.len() != 6 {
        return None;
    }
    let mut out = [0_u8; 6];
    for (slot, part) in out.iter_mut().zip(parts) {
        if part.len() != 2 || !part.bytes().all(|b| b.is_ascii_hexdigit()) {
            return None;
        }
        *slot = u8::from_str_radix(part, 16).ok()?;
    }
    Some(out)
}

#[must_use]
pub fn canonical(raw: &str) -> String {
    match ip(raw) {
        Some(Addr::V4(v)) => std::net::Ipv4Addr::from(v).to_string(),
        Some(Addr::V6(v)) => std::net::Ipv6Addr::from(v).to_string(),
        _ => mac(raw).map_or_else(
            || raw.trim().to_ascii_lowercase(),
            |m| {
                m.iter()
                    .map(|b| format!("{b:02x}"))
                    .collect::<Vec<_>>()
                    .join(":")
            },
        ),
    }
}

fn mask4(prefix: u8) -> u32 {
    if prefix == 0 {
        0
    } else {
        u32::MAX
            .checked_shl(u32::from(32_u8.saturating_sub(prefix)))
            .unwrap_or(0)
    }
}

fn mask6(prefix: u8) -> u128 {
    if prefix == 0 {
        0
    } else {
        u128::MAX
            .checked_shl(u32::from(128_u8.saturating_sub(prefix)))
            .unwrap_or(0)
    }
}

#[must_use]
pub fn net(raw: &str) -> Option<Net> {
    if let Some(m) = mac(raw) {
        return Some(Net {
            base: Addr::Mac(m),
            prefix: 48,
        });
    }
    let (addr, bits) = match raw.trim().split_once('/') {
        Some((a, b)) => (a, Some(b.parse::<u8>().ok()?)),
        None => (raw.trim(), None),
    };
    match ip(addr)? {
        Addr::V4(v) => {
            let prefix = bits.unwrap_or(32);
            (prefix <= 32).then(|| Net {
                base: Addr::V4(v & mask4(prefix)),
                prefix,
            })
        }
        Addr::V6(v) => {
            let prefix = bits.unwrap_or(128);
            (prefix <= 128).then(|| Net {
                base: Addr::V6(v & mask6(prefix)),
                prefix,
            })
        }
        Addr::Mac(_) => None,
    }
}

#[must_use]
pub fn contains(network: &Net, addr: &Addr) -> bool {
    match (network.base, addr) {
        (Addr::V4(b), Addr::V4(a)) => a & mask4(network.prefix) == b,
        (Addr::V6(b), Addr::V6(a)) => a & mask6(network.prefix) == b,
        (Addr::Mac(b), Addr::Mac(a)) => b == *a,
        _ => false,
    }
}

#[must_use]
pub fn address(raw: &str) -> Option<Addr> {
    ip(raw).or_else(|| mac(raw).map(Addr::Mac))
}

#[must_use]
pub fn is_lan(addr: &Addr) -> bool {
    match addr {
        Addr::V4(v) => LAN4.iter().any(|(b, p)| v & mask4(*p) == *b),
        Addr::V6(v) => LAN6.iter().any(|(b, p)| v & mask6(*p) == *b),
        Addr::Mac(_) => true,
    }
}
