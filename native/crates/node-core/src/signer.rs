use crate::error::{NodeError, NodeResult};
use crate::hexutil;
use crate::identity::{self, canonical};
use ed25519_dalek::{Signer, SigningKey};
use sha2::{Digest, Sha256};
use zeroize::Zeroizing;

const NONCE_BYTES: usize = 16;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SignedHeaders {
    pub ts: i64,
    pub nonce: String,
    pub signature: String,
}

pub struct DeviceKey {
    key: SigningKey,
}

impl std::fmt::Debug for DeviceKey {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("DeviceKey")
            .field("public", &self.public_hex())
            .finish_non_exhaustive()
    }
}

pub fn random_nonce() -> NodeResult<String> {
    let mut raw = [0u8; NONCE_BYTES];
    getrandom::fill(&mut raw).map_err(|_| NodeError::Key)?;
    Ok(hexutil::encode(&raw))
}

impl DeviceKey {
    pub fn generate() -> NodeResult<Self> {
        let mut seed = Zeroizing::new([0u8; 32]);
        getrandom::fill(seed.as_mut_slice()).map_err(|_| NodeError::Key)?;
        Self::from_seed(&seed)
    }

    pub fn from_seed(seed: &[u8; 32]) -> NodeResult<Self> {
        let key = SigningKey::from_bytes(seed);
        identity::parse_key(&hexutil::encode(key.verifying_key().as_bytes()))?;
        Ok(Self { key })
    }

    pub fn from_seed_hex(raw: &str) -> NodeResult<Self> {
        let bytes = Zeroizing::new(hexutil::decode(raw)?);
        let seed: &[u8; 32] = bytes.as_slice().try_into().map_err(|_| NodeError::Key)?;
        Self::from_seed(seed)
    }

    #[must_use]
    pub fn seed_hex(&self) -> Zeroizing<String> {
        Zeroizing::new(hexutil::encode(self.key.as_bytes()))
    }

    #[must_use]
    pub fn public_hex(&self) -> String {
        hexutil::encode(self.key.verifying_key().as_bytes())
    }

    pub fn pairing_code(&self) -> NodeResult<String> {
        identity::pairing_code(&self.public_hex())
    }

    pub fn sign_at(
        &self,
        node: &str,
        method: &str,
        path: &str,
        body: &[u8],
        ts: i64,
        nonce: &str,
    ) -> NodeResult<SignedHeaders> {
        let digest = hexutil::encode(&Sha256::digest(body));
        let message = canonical(node, method, path, ts, nonce, &digest)?;
        Ok(SignedHeaders {
            ts,
            nonce: nonce.to_owned(),
            signature: hexutil::encode(&self.key.sign(&message).to_bytes()),
        })
    }

    pub fn sign(
        &self,
        node: &str,
        method: &str,
        path: &str,
        body: &[u8],
        now: i64,
    ) -> NodeResult<SignedHeaders> {
        self.sign_at(node, method, path, body, now, &random_nonce()?)
    }
}
