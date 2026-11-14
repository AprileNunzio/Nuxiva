use crate::profile::Mode;

pub const MAX_SCOPE: usize = 48;
const MAX_SEGMENT: usize = 24;

pub const SATELLITE: &[&str] = &[
    "audio.capture",
    "audio.play",
    "display.render",
    "sensor.read",
    "camera.stream",
    "inference.edge",
    "telemetry.report",
];

pub const SECOND_SERVER_EXTRA: &[&str] = &[
    "node.host_full",
    "compute.lease",
    "agents.run",
    "mcp.serve",
    "storage.replica",
    "fs.read",
    "inference.host",
    "network.relay",
];

pub const ELEVATED: &[&str] = &["fs.write", "process.exec", "device.control"];

pub const FORBIDDEN_DOMAINS: &[&str] = &["admin", "vault", "identity", "users", "audit", "pairing"];

#[must_use]
pub fn valid(raw: &str) -> bool {
    if raw.is_empty() || raw.len() > MAX_SCOPE {
        return false;
    }
    let mut count = 0usize;
    for segment in raw.split('.') {
        count = count.saturating_add(1);
        let ok = !segment.is_empty()
            && segment.len() <= MAX_SEGMENT
            && segment
                .bytes()
                .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_');
        if !ok {
            return false;
        }
    }
    (2..=3).contains(&count)
}

#[must_use]
pub fn domain(raw: &str) -> &str {
    raw.split('.').next().unwrap_or("")
}

#[must_use]
pub fn forbidden(raw: &str) -> bool {
    FORBIDDEN_DOMAINS.contains(&domain(raw))
}

#[must_use]
pub fn elevated(raw: &str) -> bool {
    ELEVATED.contains(&raw)
}

#[must_use]
pub fn base_allowed(mode: Mode, raw: &str) -> bool {
    if SATELLITE.contains(&raw) {
        return true;
    }
    mode == Mode::SecondServer && SECOND_SERVER_EXTRA.contains(&raw)
}
