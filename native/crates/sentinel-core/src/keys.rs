use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{XChaCha20Poly1305, XNonce};
use hkdf::Hkdf;
use sha2::Sha256;
use zeroize::Zeroizing;

use crate::error::SentinelError;
use crate::journal::Day;

pub const KEY_LEN: usize = 32;
pub const NONCE_LEN: usize = 24;
pub const TAG_LEN: usize = 16;
const WRAP_INFO: &[u8] = b"nuxiva.sentinel.wrap.v1";
pub const WRAPPED_LEN: usize = NONCE_LEN + KEY_LEN + TAG_LEN;

pub fn random<const N: usize>() -> Result<[u8; N], SentinelError> {
    let mut out = [0_u8; N];
    getrandom::fill(&mut out).map_err(|_| SentinelError::RandomUnavailable)?;
    Ok(out)
}

pub fn cipher(key: &[u8]) -> Result<XChaCha20Poly1305, SentinelError> {
    if key.len() != KEY_LEN || key.iter().all(|b| *b == 0) {
        return Err(SentinelError::InvalidKey);
    }
    XChaCha20Poly1305::new_from_slice(key).map_err(|_| SentinelError::InvalidKey)
}

fn wrapping(master: &[u8]) -> Result<XChaCha20Poly1305, SentinelError> {
    if master.len() != KEY_LEN || master.iter().all(|b| *b == 0) {
        return Err(SentinelError::InvalidKey);
    }
    let mut okm = Zeroizing::new([0_u8; KEY_LEN]);
    Hkdf::<Sha256>::new(None, master)
        .expand(WRAP_INFO, &mut *okm)
        .map_err(|_| SentinelError::InvalidKey)?;
    cipher(&*okm)
}

fn aad(day: &Day) -> Vec<u8> {
    let mut out = b"sentinel.daykey|".to_vec();
    out.extend_from_slice(day.as_str().as_bytes());
    out
}

pub fn new_day_key(master: &[u8], day: &Day) -> Result<Vec<u8>, SentinelError> {
    let key = Zeroizing::new(random::<KEY_LEN>()?);
    let nonce = random::<NONCE_LEN>()?;
    let body = wrapping(master)?
        .encrypt(
            XNonce::from_slice(&nonce),
            Payload {
                msg: &*key,
                aad: &aad(day),
            },
        )
        .map_err(|_| SentinelError::Crypto)?;
    let mut out = nonce.to_vec();
    out.extend_from_slice(&body);
    Ok(out)
}

pub fn open_day_key(
    master: &[u8],
    day: &Day,
    wrapped: &[u8],
) -> Result<Zeroizing<Vec<u8>>, SentinelError> {
    if wrapped.len() != WRAPPED_LEN {
        return Err(SentinelError::InvalidKey);
    }
    let (nonce, body) = wrapped
        .split_at_checked(NONCE_LEN)
        .ok_or(SentinelError::InvalidKey)?;
    wrapping(master)?
        .decrypt(
            XNonce::from_slice(nonce),
            Payload {
                msg: body,
                aad: &aad(day),
            },
        )
        .map(Zeroizing::new)
        .map_err(|_| SentinelError::Crypto)
}
