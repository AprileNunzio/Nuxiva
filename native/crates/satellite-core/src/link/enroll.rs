use std::time::{Duration, SystemTime, UNIX_EPOCH};

use serde::Deserialize;
use serde_json::{Value, json};
use zeroize::{Zeroize, ZeroizeOnDrop};

use super::client::{Link, LinkError, normalize_server};
use super::tls::first_contact;
use crate::vault::Identity;

#[derive(Debug, Deserialize, Zeroize, ZeroizeOnDrop)]
pub struct EnrollFile {
    pub server: String,
    pub token: String,
    pub pin: String,
    pub expires: u64,
}

impl EnrollFile {
    pub fn parse(text: &str, now: u64) -> Result<Self, &'static str> {
        if text.len() > 4096 {
            return Err("enroll_file_invalid");
        }
        let file: Self = serde_json::from_str(text).map_err(|_| "enroll_file_invalid")?;
        let token_ok = (20..=128).contains(&file.token.len())
            && file
                .token
                .chars()
                .all(|c| c.is_ascii_alphanumeric() || matches!(c, '_' | '-'));
        let pin_ok =
            file.pin.len() == 64 && file.pin.chars().all(|c| matches!(c, '0'..='9' | 'a'..='f'));
        if !token_ok || !pin_ok || normalize_server(&file.server).is_err() {
            return Err("enroll_file_invalid");
        }
        if file.expires < now {
            return Err("enroll_file_expired");
        }
        Ok(file)
    }
}

#[must_use]
pub fn now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_secs())
}

#[must_use]
pub fn node_id(hostname: &str, name: &str) -> String {
    let raw = format!("{hostname}-{name}").to_ascii_lowercase();
    let mut out = String::with_capacity(raw.len());
    for c in raw.chars() {
        if c.is_ascii_alphanumeric() {
            out.push(c);
        } else if !out.ends_with('-') {
            out.push('-');
        }
    }
    let trimmed: String = out.trim_matches('-').chars().take(40).collect();
    let trimmed = trimmed.trim_end_matches('-').to_owned();
    if trimmed.len() < 3 {
        format!("nodo-{trimmed}").trim_end_matches('-').to_owned()
    } else {
        trimmed
    }
}

pub fn redeem(
    file: &EnrollFile,
    node_id: &str,
    name: &str,
    kind: &str,
) -> Result<Identity, LinkError> {
    let server = normalize_server(&file.server)?;
    let ca_pem = first_contact(&server, &file.pin)?;
    let link = Link::anonymous(&server, &ca_pem, Duration::from_secs(30))?;
    let reply = link.post(
        "/api/nodes/enroll",
        &json!({"token": file.token, "id": node_id, "name": name, "type": kind}),
    )?;
    let token = reply
        .get("token")
        .and_then(Value::as_str)
        .ok_or(LinkError::Protocol)?;
    Ok(Identity {
        server,
        node_id: node_id.to_owned(),
        name: name.to_owned(),
        token: token.to_owned(),
        ca_pem,
    })
}
