use aes_gcm::aead::{Aead, KeyInit, Payload};
use aes_gcm::{Aes256Gcm, Nonce};
use hkdf::Hkdf;
use sha2::Sha256;
use zeroize::Zeroizing;

use crate::error::LearnError;
use crate::signal::valid_person;

pub const MAGIC: &[u8; 7] = b"NXLRN1\n";
pub const KEY_LEN: usize = 32;
pub const NONCE_LEN: usize = 12;
pub const TAG_LEN: usize = 16;
pub const MAX_SEALED: usize = 4 * 1024 * 1024;
const HEADER: usize = MAGIC.len() + NONCE_LEN;
const MIN_SEALED: usize = HEADER + TAG_LEN;
const CONTEXT: &[u8] = b"nuxiva.display.learner.v1:";

fn key_for(master: &[u8], person: &str) -> Result<Aes256Gcm, LearnError> {
    if master.len() != KEY_LEN || master.iter().all(|b| *b == 0) {
        return Err(LearnError::Crypto);
    }
    valid_person(person)?;
    let mut info = Vec::with_capacity(CONTEXT.len().saturating_add(person.len()));
    info.extend_from_slice(CONTEXT);
    info.extend_from_slice(person.as_bytes());
    let mut okm = Zeroizing::new([0_u8; KEY_LEN]);
    Hkdf::<Sha256>::new(None, master)
        .expand(&info, &mut *okm)
        .map_err(|_| LearnError::Crypto)?;
    Aes256Gcm::new_from_slice(&*okm).map_err(|_| LearnError::Crypto)
}

fn aad(person: &str) -> Vec<u8> {
    let mut out = MAGIC.to_vec();
    out.extend_from_slice(person.as_bytes());
    out
}

pub fn seal(master: &[u8], person: &str, plaintext: &[u8]) -> Result<Vec<u8>, LearnError> {
    let cipher = key_for(master, person)?;
    let mut nonce = [0_u8; NONCE_LEN];
    getrandom::fill(&mut nonce).map_err(|_| LearnError::RandomUnavailable)?;
    let body = cipher
        .encrypt(
            Nonce::from_slice(&nonce),
            Payload {
                msg: plaintext,
                aad: &aad(person),
            },
        )
        .map_err(|_| LearnError::Crypto)?;
    let mut out = Vec::with_capacity(HEADER.saturating_add(body.len()));
    out.extend_from_slice(MAGIC);
    out.extend_from_slice(&nonce);
    out.extend_from_slice(&body);
    if out.len() > MAX_SEALED {
        return Err(LearnError::Capacity);
    }
    Ok(out)
}

pub fn open(master: &[u8], person: &str, sealed: &[u8]) -> Result<Zeroizing<Vec<u8>>, LearnError> {
    if sealed.len() > MAX_SEALED || sealed.len() < MIN_SEALED {
        return Err(LearnError::Corrupt);
    }
    let rest = sealed
        .strip_prefix(MAGIC.as_slice())
        .ok_or(LearnError::Corrupt)?;
    let (nonce, body) = rest
        .split_at_checked(NONCE_LEN)
        .ok_or(LearnError::Corrupt)?;
    let cipher = key_for(master, person)?;
    cipher
        .decrypt(
            Nonce::from_slice(nonce),
            Payload {
                msg: body,
                aad: &aad(person),
            },
        )
        .map(Zeroizing::new)
        .map_err(|_| LearnError::Crypto)
}
