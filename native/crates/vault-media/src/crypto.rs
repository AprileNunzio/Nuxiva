use chacha20poly1305::aead::{Aead, KeyInit};
use chacha20poly1305::{XChaCha20Poly1305, XNonce};
use hkdf::Hkdf;
use sha2::Sha256;
use zeroize::Zeroizing;

use crate::error::{MediaVaultError, MediaVaultResult};

pub const KEY_LEN: usize = 32;
pub const NONCE_LEN: usize = 24;
pub const CHUNK_SIZE: usize = 65536;

pub fn derive_day_camera_key(
    master_key: &[u8],
    camera_id: &str,
    day: &str,
) -> MediaVaultResult<Zeroizing<[u8; KEY_LEN]>> {
    let hk = Hkdf::<Sha256>::new(Some(b"nuxiva.vault_media.salt.v1"), master_key);
    let mut okm = Zeroizing::new([0u8; KEY_LEN]);
    let info = format!("camera:{camera_id}|day:{day}");
    hk.expand(info.as_bytes(), &mut *okm)
        .map_err(|_| MediaVaultError::KeyDerivation)?;
    Ok(okm)
}

pub fn derive_segment_key(
    day_key: &[u8; KEY_LEN],
    segment_id: &str,
) -> MediaVaultResult<Zeroizing<[u8; KEY_LEN]>> {
    let hk = Hkdf::<Sha256>::new(Some(b"nuxiva.vault_media.segment.salt"), day_key.as_slice());
    let mut okm = Zeroizing::new([0u8; KEY_LEN]);
    hk.expand(segment_id.as_bytes(), &mut *okm)
        .map_err(|_| MediaVaultError::KeyDerivation)?;
    Ok(okm)
}

#[must_use]
pub fn build_chunk_nonce(base_nonce: &[u8; NONCE_LEN], chunk_index: u64) -> [u8; NONCE_LEN] {
    let mut nonce = *base_nonce;
    let idx_bytes = chunk_index.to_be_bytes();
    for (i, b) in idx_bytes.iter().enumerate() {
        if let Some(target) = nonce.get_mut(NONCE_LEN.saturating_sub(8).saturating_add(i)) {
            *target ^= *b;
        }
    }
    nonce
}

pub fn encrypt_chunk(
    key: &[u8; KEY_LEN],
    base_nonce: &[u8; NONCE_LEN],
    chunk_index: u64,
    plaintext: &[u8],
) -> MediaVaultResult<Vec<u8>> {
    let cipher = XChaCha20Poly1305::new_from_slice(key)
        .map_err(|e| MediaVaultError::Crypto(e.to_string()))?;
    let nonce_bytes = build_chunk_nonce(base_nonce, chunk_index);
    let nonce = XNonce::from_slice(&nonce_bytes);
    cipher
        .encrypt(nonce, plaintext)
        .map_err(|e| MediaVaultError::Crypto(e.to_string()))
}

pub fn decrypt_chunk(
    key: &[u8; KEY_LEN],
    base_nonce: &[u8; NONCE_LEN],
    chunk_index: u64,
    ciphertext: &[u8],
) -> MediaVaultResult<Vec<u8>> {
    let cipher = XChaCha20Poly1305::new_from_slice(key)
        .map_err(|e| MediaVaultError::Crypto(e.to_string()))?;
    let nonce_bytes = build_chunk_nonce(base_nonce, chunk_index);
    let nonce = XNonce::from_slice(&nonce_bytes);
    cipher
        .decrypt(nonce, ciphertext)
        .map_err(|_| MediaVaultError::ChunkCorrupted)
}
