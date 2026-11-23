use serde::{Deserialize, Serialize};

use crate::{SELF_KEY, normalize_mac, randomized};

#[derive(Debug, Clone, Default, Deserialize)]
pub struct Known {
    pub key: String,
    #[serde(default)]
    pub mac: Option<String>,
    #[serde(default)]
    pub ip: Option<String>,
    #[serde(default)]
    pub hostname: Option<String>,
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct Seen {
    #[serde(default)]
    pub mac: Option<String>,
    #[serde(default)]
    pub ip: Option<String>,
    #[serde(default)]
    pub hostname: Option<String>,
    #[serde(default)]
    pub own: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Resolution {
    pub key: String,
    pub mac: Option<String>,
    pub randomized: bool,
    pub merge: Vec<String>,
}

fn host(value: Option<&String>) -> Option<String> {
    let name = value?.trim().trim_end_matches('.').to_ascii_lowercase();
    let name = name.strip_suffix(".local").unwrap_or(&name).to_string();
    (!name.is_empty() && name.len() <= 253).then_some(name)
}

fn mac_of(known: &Known) -> Option<String> {
    known.mac.as_deref().and_then(normalize_mac)
}

fn by_host<'a>(known: &'a [Known], name: &str, skip: &str) -> Option<&'a Known> {
    known.iter().find(|k| {
        k.key != skip
            && host(k.hostname.as_ref()).as_deref() == Some(name)
            && mac_of(k).is_none_or(|m| randomized(&m))
    })
}

fn orphans(known: &[Known], ip: Option<&str>, keep: &str) -> Vec<String> {
    let Some(ip) = ip else { return Vec::new() };
    known
        .iter()
        .filter(|k| {
            k.key != keep
                && k.key.starts_with("ip:")
                && k.ip.as_deref() == Some(ip)
                && mac_of(k).is_none()
        })
        .map(|k| k.key.clone())
        .collect()
}

#[must_use]
pub fn resolve(known: &[Known], seen: &Seen) -> Option<Resolution> {
    let ip = seen
        .ip
        .as_deref()
        .map(str::trim)
        .filter(|v| !v.is_empty() && v.len() <= 45);
    let name = host(seen.hostname.as_ref());
    if seen.own {
        return Some(Resolution {
            key: SELF_KEY.into(),
            mac: None,
            randomized: false,
            merge: orphans(known, ip, SELF_KEY),
        });
    }
    if let Some(mac) = seen.mac.as_deref().and_then(normalize_mac) {
        let random = randomized(&mac);
        let exact = known.iter().any(|k| k.key == mac);
        let key = if !exact && random {
            name.as_deref()
                .and_then(|n| by_host(known, n, &mac))
                .map_or_else(|| mac.clone(), |k| k.key.clone())
        } else {
            mac.clone()
        };
        let merge = orphans(known, ip, &key);
        return Some(Resolution {
            key,
            mac: Some(mac),
            randomized: random,
            merge,
        });
    }
    let ip = ip?;
    if let Some(found) = name.as_deref().and_then(|n| by_host(known, n, "")) {
        return Some(Resolution {
            key: found.key.clone(),
            mac: None,
            randomized: false,
            merge: Vec::new(),
        });
    }
    let key = known
        .iter()
        .find(|k| {
            k.ip.as_deref() == Some(ip)
                && (k.key.starts_with("ip:") || mac_of(k).is_some_and(|m| !randomized(&m)))
        })
        .map_or_else(|| format!("ip:{ip}"), |k| k.key.clone());
    Some(Resolution {
        key,
        mac: None,
        randomized: false,
        merge: Vec::new(),
    })
}
