use base64::Engine;
use base64::engine::general_purpose::STANDARD;
use nuxiva_node_core::hexutil;
use sha2::{Digest, Sha256};

use crate::error::{MobileError, MobileResult};

const BEGIN: &str = "-----BEGIN CERTIFICATE-----";
const END: &str = "-----END CERTIFICATE-----";
const PEM_LIMIT: usize = 65_536;
const INVALID: &str = "enroll_ca_invalid";

fn invalid() -> MobileError {
    MobileError::code(INVALID)
}

fn der_length(der: &[u8]) -> Option<usize> {
    if der.first() != Some(&0x30) {
        return None;
    }
    let first = *der.get(1)?;
    if first < 0x80 {
        return 2usize.checked_add(usize::from(first));
    }
    let count = usize::from(first & 0x7f);
    if count == 0 || count > 4 {
        return None;
    }
    let mut length = 0usize;
    for byte in der.get(2..2usize.checked_add(count)?)? {
        length = length.checked_mul(256)?.checked_add(usize::from(*byte))?;
    }
    2usize.checked_add(count)?.checked_add(length)
}

fn decode_pem(pem: &str) -> MobileResult<Vec<u8>> {
    if pem.len() > PEM_LIMIT {
        return Err(invalid());
    }
    let start = pem.find(BEGIN).ok_or_else(invalid)?;
    let body = pem
        .get(start.checked_add(BEGIN.len()).ok_or_else(invalid)?..)
        .ok_or_else(invalid)?;
    let end = body.find(END).ok_or_else(invalid)?;
    let encoded: String = body
        .get(..end)
        .ok_or_else(invalid)?
        .chars()
        .filter(|c| !c.is_ascii_whitespace())
        .collect();
    let der = STANDARD.decode(encoded).map_err(|_| invalid())?;
    if der_length(&der) != Some(der.len()) {
        return Err(invalid());
    }
    Ok(der)
}

#[uniffi::export]
pub fn ca_der(pem: &str) -> Result<Vec<u8>, MobileError> {
    decode_pem(pem)
}

#[uniffi::export]
pub fn ca_fingerprint(pem: &str) -> Result<String, MobileError> {
    let der = decode_pem(pem)?;
    Ok(hexutil::encode(&Sha256::digest(&der)))
}

#[uniffi::export]
#[must_use]
pub fn pin_matches(expected: &str, actual: &str) -> bool {
    let left = expected.to_ascii_lowercase();
    let right = actual.to_ascii_lowercase();
    if left.len() != right.len() || left.is_empty() {
        return false;
    }
    left.bytes()
        .zip(right.bytes())
        .fold(0u8, |acc, (a, b)| acc | (a ^ b))
        == 0
}
