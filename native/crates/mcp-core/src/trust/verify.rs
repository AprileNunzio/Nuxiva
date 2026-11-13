use base64::Engine;
use base64::engine::general_purpose::STANDARD;
use ed25519_dalek::{Signature, Signer, SigningKey, VerifyingKey};
use serde::{Deserialize, Serialize};

use super::catalog::Catalog;
use crate::error::{McpError, McpResult};

pub const MAX_PAYLOAD: usize = 1024 * 1024;
const SKEW_SECS: u64 = 300;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SignedCatalog {
    pub payload: String,
    pub signature: String,
}

pub fn sign_catalog(catalog: &Catalog, key: &SigningKey) -> McpResult<SignedCatalog> {
    catalog.validate()?;
    let payload = serde_json::to_string(catalog).map_err(|_| McpError::Serialize)?;
    let signature = key.sign(payload.as_bytes());
    Ok(SignedCatalog {
        payload,
        signature: STANDARD.encode(signature.to_bytes()),
    })
}

pub fn verify_catalog(
    signed: &SignedCatalog,
    public_key: &[u8; 32],
    now_secs: u64,
    last_serial: u64,
) -> McpResult<Catalog> {
    if signed.payload.len() > MAX_PAYLOAD {
        return Err(McpError::TooLarge);
    }
    let key = VerifyingKey::from_bytes(public_key).map_err(|_| McpError::SignatureInvalid)?;
    let raw = STANDARD
        .decode(signed.signature.as_bytes())
        .map_err(|_| McpError::SignatureInvalid)?;
    let bytes: [u8; 64] = raw.try_into().map_err(|_| McpError::SignatureInvalid)?;
    key.verify_strict(signed.payload.as_bytes(), &Signature::from_bytes(&bytes))
        .map_err(|_| McpError::SignatureInvalid)?;
    let catalog: Catalog =
        serde_json::from_str(&signed.payload).map_err(|_| McpError::InvalidSettings)?;
    catalog.validate()?;
    if now_secs > catalog.not_after {
        return Err(McpError::CatalogExpired);
    }
    if catalog.issued_at > now_secs.saturating_add(SKEW_SECS) || catalog.serial < last_serial {
        return Err(McpError::SignatureInvalid);
    }
    Ok(catalog)
}
