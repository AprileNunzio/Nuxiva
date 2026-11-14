use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{XChaCha20Poly1305, XNonce};
use hkdf::Hkdf;
use sha2::Sha256;
use zeroize::Zeroizing;

use crate::error::{KnowledgeError, KnowledgeResult};

pub const NONCE_LEN: usize = 24;
const SALT: &[u8] = b"nuxiva.knowledge.v1";

pub struct MasterKey {
    key: Zeroizing<[u8; 32]>,
}

impl std::fmt::Debug for MasterKey {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("MasterKey(..)")
    }
}

pub struct OwnerKey {
    key: Zeroizing<[u8; 32]>,
}

impl std::fmt::Debug for OwnerKey {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("OwnerKey(..)")
    }
}

impl MasterKey {
    pub fn random() -> KnowledgeResult<Self> {
        let mut key = Zeroizing::new([0_u8; 32]);
        getrandom::fill(key.as_mut()).map_err(|_| KnowledgeError::Seal)?;
        Ok(Self { key })
    }

    #[must_use]
    pub fn from_key(key: [u8; 32]) -> Self {
        Self {
            key: Zeroizing::new(key),
        }
    }

    fn expand(&self, info: &[u8], out: &mut [u8]) -> KnowledgeResult<()> {
        Hkdf::<Sha256>::new(Some(SALT), self.key.as_ref())
            .expand(info, out)
            .map_err(|_| KnowledgeError::Seal)
    }

    pub fn owner(&self, owner: &str) -> KnowledgeResult<OwnerKey> {
        let mut key = Zeroizing::new([0_u8; 32]);
        self.expand(format!("owner:{owner}").as_bytes(), key.as_mut())?;
        Ok(OwnerKey { key })
    }

    pub fn file_name(&self, owner: &str) -> KnowledgeResult<String> {
        let mut out = [0_u8; 16];
        self.expand(format!("file:{owner}").as_bytes(), &mut out)?;
        Ok(crate::text::hex(&out))
    }
}

impl OwnerKey {
    pub fn seal(&self, aad: &[u8], plain: &[u8]) -> KnowledgeResult<(Vec<u8>, Vec<u8>)> {
        let mut nonce = [0_u8; NONCE_LEN];
        getrandom::fill(&mut nonce).map_err(|_| KnowledgeError::Seal)?;
        let data = XChaCha20Poly1305::new(self.key.as_ref().into())
            .encrypt(XNonce::from_slice(&nonce), Payload { msg: plain, aad })
            .map_err(|_| KnowledgeError::Seal)?;
        Ok((nonce.to_vec(), data))
    }

    pub fn open(
        &self,
        aad: &[u8],
        nonce: &[u8],
        data: &[u8],
    ) -> KnowledgeResult<Zeroizing<Vec<u8>>> {
        if nonce.len() != NONCE_LEN {
            return Err(KnowledgeError::Seal);
        }
        XChaCha20Poly1305::new(self.key.as_ref().into())
            .decrypt(XNonce::from_slice(nonce), Payload { msg: data, aad })
            .map(Zeroizing::new)
            .map_err(|_| KnowledgeError::Seal)
    }
}
