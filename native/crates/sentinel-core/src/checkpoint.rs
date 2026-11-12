use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use zeroize::Zeroizing;

use crate::error::SentinelError;
use crate::journal::{Day, Head};

fn message(day: &Day, count: usize, head: &Head) -> Vec<u8> {
    format!(
        "nuxiva.sentinel.checkpoint.v1|{}|{count}|{}",
        day.as_str(),
        head.hex()
    )
    .into_bytes()
}

fn signing(seed: &[u8]) -> Result<SigningKey, SentinelError> {
    let bytes: Zeroizing<[u8; 32]> =
        Zeroizing::new(seed.try_into().map_err(|_| SentinelError::InvalidKey)?);
    Ok(SigningKey::from_bytes(&bytes))
}

pub fn public_key(seed: &[u8]) -> Result<[u8; 32], SentinelError> {
    Ok(signing(seed)?.verifying_key().to_bytes())
}

pub fn sign(seed: &[u8], day: &Day, count: usize, head: &Head) -> Result<[u8; 64], SentinelError> {
    Ok(signing(seed)?.sign(&message(day, count, head)).to_bytes())
}

pub fn verify(
    public: &[u8],
    day: &Day,
    count: usize,
    head: &Head,
    signature: &[u8],
) -> Result<(), SentinelError> {
    let key: [u8; 32] = public.try_into().map_err(|_| SentinelError::InvalidKey)?;
    let key = VerifyingKey::from_bytes(&key).map_err(|_| SentinelError::InvalidKey)?;
    let sig = Signature::from_slice(signature).map_err(|_| SentinelError::Signature)?;
    key.verify(&message(day, count, head), &sig)
        .map_err(|_| SentinelError::Signature)
}
