use crate::error::{NodeError, NodeResult};
use crate::hexutil;
use ed25519_dalek::{Signature, VerifyingKey};
use sha2::{Digest, Sha256};

pub const DOMAIN: &str = "nuxiva-node-v1";
pub const SKEW: i64 = 60;
const MAX_FIELD: usize = 256;

fn clean(value: &str, min: usize) -> NodeResult<&str> {
    if value.len() < min || value.len() > MAX_FIELD || value.chars().any(char::is_control) {
        return Err(NodeError::Field);
    }
    Ok(value)
}

pub fn parse_key(raw: &str) -> NodeResult<VerifyingKey> {
    let bytes: [u8; 32] = hexutil::decode(raw)?
        .try_into()
        .map_err(|_| NodeError::Key)?;
    let key = VerifyingKey::from_bytes(&bytes).map_err(|_| NodeError::Key)?;
    if key.is_weak() {
        return Err(NodeError::Key);
    }
    Ok(key)
}

pub fn fingerprint(raw: &str) -> NodeResult<String> {
    let key = parse_key(raw)?;
    let digest = Sha256::digest(key.as_bytes());
    let hex = hexutil::encode(digest.get(..6).unwrap_or(&[])).to_uppercase();
    Ok(hex
        .as_bytes()
        .chunks(4)
        .map(|c| String::from_utf8_lossy(c).into_owned())
        .collect::<Vec<_>>()
        .join("-"))
}

pub fn pairing_code(raw: &str) -> NodeResult<String> {
    let key = parse_key(raw)?;
    let digest = Sha256::digest(key.as_bytes());
    let head: [u8; 8] = digest
        .get(..8)
        .and_then(|s| s.try_into().ok())
        .ok_or(NodeError::Key)?;
    Ok(format!("{:06}", u64::from_be_bytes(head) % 1_000_000))
}

pub fn canonical(
    node: &str,
    method: &str,
    path: &str,
    ts: i64,
    nonce: &str,
    body_sha256: &str,
) -> NodeResult<Vec<u8>> {
    let node = clean(node, 3)?;
    let path = clean(path, 1)?;
    let nonce = clean(nonce, 16)?;
    if method.is_empty()
        || method.len() > 8
        || !method.bytes().all(|b| b.is_ascii_uppercase())
        || body_sha256.len() != 64
        || hexutil::decode(body_sha256).is_err()
        || nonce
            .bytes()
            .any(|b| !(b.is_ascii_alphanumeric() || b == b'-' || b == b'_'))
    {
        return Err(NodeError::Field);
    }
    Ok(format!("{DOMAIN}\n{node}\n{method}\n{path}\n{ts}\n{nonce}\n{body_sha256}").into_bytes())
}

#[allow(clippy::too_many_arguments)]
pub fn verify_request(
    key_hex: &str,
    signature_hex: &str,
    node: &str,
    method: &str,
    path: &str,
    ts: i64,
    nonce: &str,
    body_sha256: &str,
    now: i64,
) -> NodeResult<()> {
    if now.abs_diff(ts) > SKEW.unsigned_abs() {
        return Err(NodeError::Clock);
    }
    let key = parse_key(key_hex)?;
    let message = canonical(node, method, path, ts, nonce, body_sha256)?;
    let raw: [u8; 64] = hexutil::decode(signature_hex)?
        .try_into()
        .map_err(|_| NodeError::Signature)?;
    key.verify_strict(&message, &Signature::from_bytes(&raw))
        .map_err(|_| NodeError::Signature)
}
