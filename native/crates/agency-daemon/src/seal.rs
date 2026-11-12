use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{XChaCha20Poly1305, XNonce};
use zeroize::Zeroizing;

use crate::error::AgencyError;

const MAGIC: &[u8; 4] = b"NXF1";
const NONCE: usize = 24;

#[derive(Clone)]
pub struct Sealer {
    key: Zeroizing<[u8; 32]>,
}

impl std::fmt::Debug for Sealer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Sealer(..)")
    }
}

impl Sealer {
    #[must_use]
    pub fn new(key: [u8; 32]) -> Self {
        Self {
            key: Zeroizing::new(key),
        }
    }

    fn cipher(&self) -> Result<XChaCha20Poly1305, AgencyError> {
        XChaCha20Poly1305::new_from_slice(self.key.as_slice()).map_err(|_| AgencyError::Sealed)
    }

    pub fn seal(&self, label: &str, plain: &[u8]) -> Result<Vec<u8>, AgencyError> {
        let mut nonce = [0u8; NONCE];
        getrandom::fill(&mut nonce).map_err(|e| std::io::Error::other(e.to_string()))?;
        let body = self
            .cipher()?
            .encrypt(
                XNonce::from_slice(&nonce),
                Payload {
                    msg: plain,
                    aad: label.as_bytes(),
                },
            )
            .map_err(|_| AgencyError::Sealed)?;
        let mut out =
            Vec::with_capacity(MAGIC.len().saturating_add(NONCE).saturating_add(body.len()));
        out.extend_from_slice(MAGIC);
        out.extend_from_slice(&nonce);
        out.extend_from_slice(&body);
        Ok(out)
    }

    pub fn open(&self, label: &str, sealed: &[u8]) -> Result<Zeroizing<Vec<u8>>, AgencyError> {
        let rest = sealed.strip_prefix(MAGIC).ok_or(AgencyError::Sealed)?;
        let (nonce, body) = rest.split_at_checked(NONCE).ok_or(AgencyError::Sealed)?;
        self.cipher()?
            .decrypt(
                XNonce::from_slice(nonce),
                Payload {
                    msg: body,
                    aad: label.as_bytes(),
                },
            )
            .map(Zeroizing::new)
            .map_err(|_| AgencyError::Sealed)
    }
}
