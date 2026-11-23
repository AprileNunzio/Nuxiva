use nuxiva_node_core::DeviceKey;
use nuxiva_node_core::hexutil;
use zeroize::Zeroizing;

use crate::error::{MobileError, MobileResult};

const NODE_PREFIX: &str = "ios";
const SLUG_LIMIT: usize = 30;

#[derive(Debug, Clone, PartialEq, Eq, uniffi::Record)]
pub struct SignedRequest {
    pub node: String,
    pub ts: i64,
    pub nonce: String,
    pub signature: String,
}

#[derive(Debug, uniffi::Object)]
pub struct DeviceIdentity {
    key: DeviceKey,
}

#[uniffi::export]
impl DeviceIdentity {
    #[uniffi::constructor]
    pub fn generate() -> Result<Self, MobileError> {
        Ok(Self {
            key: DeviceKey::generate()?,
        })
    }

    #[uniffi::constructor]
    pub fn from_seed_hex(seed: String) -> Result<Self, MobileError> {
        let seed = Zeroizing::new(seed);
        Ok(Self {
            key: DeviceKey::from_seed_hex(&seed)?,
        })
    }

    #[must_use]
    pub fn seed_hex(&self) -> String {
        self.key.seed_hex().to_string()
    }

    #[must_use]
    pub fn public_hex(&self) -> String {
        self.key.public_hex()
    }

    pub fn sign(
        &self,
        node: String,
        method: &str,
        path: &str,
        body: &[u8],
        now: i64,
    ) -> Result<SignedRequest, MobileError> {
        let signed = self.key.sign(&node, method, path, body, now)?;
        Ok(SignedRequest {
            node,
            ts: signed.ts,
            nonce: signed.nonce,
            signature: signed.signature,
        })
    }
}

fn slug(model: &str) -> String {
    let mut out = String::new();
    let mut dash = false;
    for c in model.to_ascii_lowercase().chars() {
        if c.is_ascii_alphanumeric() {
            out.push(c);
            dash = false;
        } else if !dash && !out.is_empty() {
            out.push('-');
            dash = true;
        }
    }
    let cut: String = out.chars().take(SLUG_LIMIT).collect();
    let trimmed = cut.trim_matches('-');
    if trimmed.is_empty() {
        "device".to_owned()
    } else {
        trimmed.to_owned()
    }
}

#[must_use]
pub fn node_id_with(model: &str, suffix: [u8; 3]) -> String {
    format!("{NODE_PREFIX}-{}-{}", slug(model), hexutil::encode(&suffix))
}

fn random_suffix() -> MobileResult<[u8; 3]> {
    let mut raw = [0u8; 3];
    getrandom::fill(&mut raw).map_err(|_| MobileError::code("node.error.key"))?;
    Ok(raw)
}

#[uniffi::export]
pub fn new_node_id(model: &str) -> Result<String, MobileError> {
    Ok(node_id_with(model, random_suffix()?))
}
