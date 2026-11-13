use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{XChaCha20Poly1305, XNonce};
use serde::{Deserialize, Serialize};
use zeroize::{Zeroize, Zeroizing};

use crate::error::{ContextError, ContextResult};

pub const NONCE_LEN: usize = 24;
const TAG: &[u8] = b"nuxiva.context.vitals.v1";

#[derive(Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Sealed {
    pub nonce: Vec<u8>,
    pub data: Vec<u8>,
}

impl std::fmt::Debug for Sealed {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Sealed(..)")
    }
}

#[derive(Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Vitals {
    pub allergies: Vec<String>,
    pub diet: Option<String>,
    pub notes: Option<String>,
}

impl std::fmt::Debug for Vitals {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Vitals(..)")
    }
}

impl Zeroize for Vitals {
    fn zeroize(&mut self) {
        self.allergies.iter_mut().for_each(Zeroize::zeroize);
        self.allergies.clear();
        self.diet.zeroize();
        self.notes.zeroize();
    }
}

pub struct Sealer {
    key: Zeroizing<[u8; 32]>,
}

impl std::fmt::Debug for Sealer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Sealer(..)")
    }
}

impl Sealer {
    pub fn random() -> ContextResult<Self> {
        let mut key = Zeroizing::new([0_u8; 32]);
        getrandom::fill(key.as_mut()).map_err(|_| ContextError::Seal)?;
        Ok(Self { key })
    }

    #[must_use]
    pub fn from_key(key: [u8; 32]) -> Self {
        Self {
            key: Zeroizing::new(key),
        }
    }

    fn cipher(&self) -> XChaCha20Poly1305 {
        XChaCha20Poly1305::new(self.key.as_ref().into())
    }

    pub fn seal(&self, vitals: &Vitals) -> ContextResult<Sealed> {
        let plain = Zeroizing::new(serde_json::to_vec(vitals).map_err(|_| ContextError::Seal)?);
        let mut nonce = [0_u8; NONCE_LEN];
        getrandom::fill(&mut nonce).map_err(|_| ContextError::Seal)?;
        let data = self
            .cipher()
            .encrypt(
                XNonce::from_slice(&nonce),
                Payload {
                    msg: plain.as_slice(),
                    aad: TAG,
                },
            )
            .map_err(|_| ContextError::Seal)?;
        Ok(Sealed {
            nonce: nonce.to_vec(),
            data,
        })
    }

    pub fn open(&self, sealed: &Sealed) -> ContextResult<Zeroizing<Vitals>> {
        if sealed.nonce.len() != NONCE_LEN {
            return Err(ContextError::Seal);
        }
        let plain = Zeroizing::new(
            self.cipher()
                .decrypt(
                    XNonce::from_slice(&sealed.nonce),
                    Payload {
                        msg: sealed.data.as_slice(),
                        aad: TAG,
                    },
                )
                .map_err(|_| ContextError::Seal)?,
        );
        serde_json::from_slice(plain.as_slice())
            .map(Zeroizing::new)
            .map_err(|_| ContextError::Seal)
    }
}
