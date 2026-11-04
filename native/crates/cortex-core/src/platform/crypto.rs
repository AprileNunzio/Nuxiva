use std::fmt;

use aes_gcm::aead::{Aead, KeyInit, Payload};
use aes_gcm::{Aes256Gcm, Nonce};
use ed25519_dalek::{Signature, Signer as _, SigningKey, VerifyingKey};
use hkdf::Hkdf;
use sha2::Sha256;
use zeroize::Zeroizing;

use super::error::{CortexError, CortexResult};

pub const KEY_LEN: usize = 32;
pub const NONCE_LEN: usize = 12;
pub const TAG_LEN: usize = 16;
pub const PUBLIC_KEY_LEN: usize = 32;
pub const SIGNATURE_LEN: usize = 64;

fn random_array<const N: usize>() -> CortexResult<[u8; N]> {
    let mut buffer = [0_u8; N];
    getrandom::fill(&mut buffer).map_err(|_| CortexError::RandomUnavailable)?;
    Ok(buffer)
}

pub struct SecretKey {
    bytes: Zeroizing<[u8; KEY_LEN]>,
}

impl fmt::Debug for SecretKey {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("SecretKey(..)")
    }
}

impl SecretKey {
    pub fn from_slice(material: &[u8]) -> CortexResult<Self> {
        let bytes: [u8; KEY_LEN] = material
            .try_into()
            .map_err(|_| CortexError::InvalidKeyLength)?;
        Ok(Self {
            bytes: Zeroizing::new(bytes),
        })
    }

    pub fn generate() -> CortexResult<Self> {
        Ok(Self {
            bytes: Zeroizing::new(random_array::<KEY_LEN>()?),
        })
    }

    pub fn derive(master: &[u8], context: &[u8]) -> CortexResult<Self> {
        if master.is_empty() {
            return Err(CortexError::InvalidKeyLength);
        }
        let expander = Hkdf::<Sha256>::new(None, master);
        let mut okm = Zeroizing::new([0_u8; KEY_LEN]);
        expander
            .expand(context, &mut *okm)
            .map_err(|_| CortexError::KeyDerivationFailed)?;
        Ok(Self { bytes: okm })
    }

    #[must_use]
    pub fn expose(&self) -> &[u8; KEY_LEN] {
        &self.bytes
    }
}

fn cipher(key: &SecretKey) -> CortexResult<Aes256Gcm> {
    Aes256Gcm::new_from_slice(key.expose()).map_err(|_| CortexError::InvalidKeyLength)
}

pub fn seal(key: &SecretKey, associated_data: &[u8], plaintext: &[u8]) -> CortexResult<Vec<u8>> {
    let nonce_bytes = random_array::<NONCE_LEN>()?;
    let ciphertext = cipher(key)?
        .encrypt(
            Nonce::from_slice(&nonce_bytes),
            Payload {
                msg: plaintext,
                aad: associated_data,
            },
        )
        .map_err(|_| CortexError::EncryptionFailed)?;
    let mut sealed = Vec::with_capacity(NONCE_LEN.saturating_add(ciphertext.len()));
    sealed.extend_from_slice(&nonce_bytes);
    sealed.extend_from_slice(&ciphertext);
    Ok(sealed)
}

pub fn open(key: &SecretKey, associated_data: &[u8], sealed: &[u8]) -> CortexResult<Vec<u8>> {
    if sealed.len() < NONCE_LEN.saturating_add(TAG_LEN) {
        return Err(CortexError::MalformedCiphertext);
    }
    let (nonce_bytes, ciphertext) = sealed.split_at(NONCE_LEN);
    cipher(key)?
        .decrypt(
            Nonce::from_slice(nonce_bytes),
            Payload {
                msg: ciphertext,
                aad: associated_data,
            },
        )
        .map_err(|_| CortexError::DecryptionFailed)
}

pub struct Signer {
    key: SigningKey,
}

impl fmt::Debug for Signer {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("Signer(..)")
    }
}

impl Signer {
    pub fn from_seed(seed: &[u8]) -> CortexResult<Self> {
        let bytes: Zeroizing<[u8; KEY_LEN]> =
            Zeroizing::new(seed.try_into().map_err(|_| CortexError::InvalidKeyLength)?);
        Ok(Self {
            key: SigningKey::from_bytes(&bytes),
        })
    }

    pub fn generate() -> CortexResult<Self> {
        let seed = Zeroizing::new(random_array::<KEY_LEN>()?);
        Ok(Self {
            key: SigningKey::from_bytes(&seed),
        })
    }

    #[must_use]
    pub fn public_key(&self) -> [u8; PUBLIC_KEY_LEN] {
        self.key.verifying_key().to_bytes()
    }

    #[must_use]
    pub fn sign(&self, message: &[u8]) -> [u8; SIGNATURE_LEN] {
        self.key.sign(message).to_bytes()
    }
}

pub fn verify(public_key: &[u8], message: &[u8], signature: &[u8]) -> CortexResult<bool> {
    let key_bytes: [u8; PUBLIC_KEY_LEN] = public_key
        .try_into()
        .map_err(|_| CortexError::InvalidKeyLength)?;
    let verifying =
        VerifyingKey::from_bytes(&key_bytes).map_err(|_| CortexError::InvalidKeyLength)?;
    let parsed = Signature::from_slice(signature).map_err(|_| CortexError::MalformedSignature)?;
    Ok(verifying.verify_strict(message, &parsed).is_ok())
}

#[cfg(test)]
mod tests {
    use super::{CortexError, SecretKey, Signer, TAG_LEN, open, seal, verify};

    #[test]
    fn seal_then_open_round_trips_and_binds_associated_data() -> Result<(), CortexError> {
        let key = SecretKey::generate()?;
        let sealed = seal(&key, b"neuron:1", b"payload")?;
        assert_eq!(open(&key, b"neuron:1", &sealed)?, b"payload".to_vec());
        assert_eq!(
            open(&key, b"neuron:2", &sealed),
            Err(CortexError::DecryptionFailed)
        );
        Ok(())
    }

    #[test]
    fn each_seal_uses_a_fresh_nonce() -> Result<(), CortexError> {
        let key = SecretKey::generate()?;
        assert_ne!(seal(&key, b"", b"same")?, seal(&key, b"", b"same")?);
        Ok(())
    }

    #[test]
    fn tampering_and_truncation_are_detected() -> Result<(), CortexError> {
        let key = SecretKey::generate()?;
        let mut sealed = seal(&key, b"", b"payload")?;
        if let Some(last) = sealed.last_mut() {
            *last ^= 1;
        }
        assert_eq!(open(&key, b"", &sealed), Err(CortexError::DecryptionFailed));
        assert_eq!(
            open(&key, b"", sealed.get(..TAG_LEN).unwrap_or_default()),
            Err(CortexError::MalformedCiphertext)
        );
        let other = SecretKey::generate()?;
        let fresh = seal(&key, b"", b"payload")?;
        assert_eq!(
            open(&other, b"", &fresh),
            Err(CortexError::DecryptionFailed)
        );
        Ok(())
    }

    #[test]
    fn key_derivation_is_deterministic_and_context_separated() -> Result<(), CortexError> {
        let first = SecretKey::derive(b"master", b"neurons")?;
        let second = SecretKey::derive(b"master", b"neurons")?;
        let other = SecretKey::derive(b"master", b"skills")?;
        assert_eq!(first.expose(), second.expose());
        assert_ne!(first.expose(), other.expose());
        assert_eq!(
            SecretKey::derive(b"", b"neurons").map(|_| ()),
            Err(CortexError::InvalidKeyLength)
        );
        assert_eq!(
            SecretKey::from_slice(&[0_u8; 31]).map(|_| ()),
            Err(CortexError::InvalidKeyLength)
        );
        Ok(())
    }

    #[test]
    fn signatures_verify_only_for_the_signed_message() -> Result<(), CortexError> {
        let signer = Signer::from_seed(&[7_u8; 32])?;
        let signature = signer.sign(b"skill");
        assert_eq!(verify(&signer.public_key(), b"skill", &signature), Ok(true));
        assert_eq!(
            verify(&signer.public_key(), b"skill!", &signature),
            Ok(false)
        );
        assert_eq!(
            verify(
                &signer.public_key(),
                b"skill",
                signature.get(..10).unwrap_or_default()
            ),
            Err(CortexError::MalformedSignature)
        );
        let stranger = Signer::generate()?;
        assert_eq!(
            verify(&stranger.public_key(), b"skill", &signature),
            Ok(false)
        );
        Ok(())
    }
}
