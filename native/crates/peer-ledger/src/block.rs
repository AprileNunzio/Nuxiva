use crate::error::{LedgerError, LedgerResult};
use ed25519_dalek::{Signature, VerifyingKey};
use nuxiva_node_core::hexutil;
use nuxiva_node_core::identity::parse_key;
use nuxiva_peer_core::PeerKey;
use nuxiva_peer_core::addr::check_addrs;
use nuxiva_peer_core::ident::check_id;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

pub const DOMAIN: &str = "nuxiva-ledger-v1";
pub const GENESIS: &str = "0000000000000000000000000000000000000000000000000000000000000000";
pub const HASH_LEN: usize = 64;
pub const SIG_LEN: usize = 128;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Block {
    pub author: String,
    pub index: u64,
    pub prev: String,
    pub ts: i64,
    pub addrs: Vec<String>,
    pub sig: String,
}

fn is_hex(text: &str, len: usize) -> bool {
    text.len() == len && text.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f'))
}

fn addrs_digest(addrs: &[String]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(addrs.len().to_be_bytes());
    for addr in addrs {
        hasher.update(addr.len().to_be_bytes());
        hasher.update(addr.as_bytes());
    }
    hexutil::encode(&hasher.finalize())
}

impl Block {
    #[must_use]
    pub fn signed_bytes(
        author: &str,
        index: u64,
        prev: &str,
        ts: i64,
        addrs: &[String],
    ) -> Vec<u8> {
        let digest = addrs_digest(addrs);
        format!("{DOMAIN}\n{author}\n{index}\n{prev}\n{ts}\n{digest}").into_bytes()
    }

    pub fn seal(
        key: &PeerKey,
        index: u64,
        prev: &str,
        ts: i64,
        addrs: Vec<String>,
    ) -> LedgerResult<Self> {
        check_addrs(&addrs)?;
        let sig = key.sign(&Self::signed_bytes(key.id(), index, prev, ts, &addrs));
        Ok(Self {
            author: key.id().to_owned(),
            index,
            prev: prev.to_owned(),
            ts,
            addrs,
            sig,
        })
    }

    #[must_use]
    pub fn hash(&self) -> String {
        let mut hasher = Sha256::new();
        hasher.update(Self::signed_bytes(
            &self.author,
            self.index,
            &self.prev,
            self.ts,
            &self.addrs,
        ));
        hasher.update(self.sig.as_bytes());
        hexutil::encode(&hasher.finalize())
    }

    pub fn check_shape(&self) -> LedgerResult<()> {
        check_id(&self.author)?;
        if !is_hex(&self.prev, HASH_LEN) || !is_hex(&self.sig, SIG_LEN) || self.ts < 0 {
            return Err(LedgerError::Field);
        }
        check_addrs(&self.addrs)?;
        Ok(())
    }

    pub fn verify(&self) -> LedgerResult<()> {
        self.check_shape()?;
        let key: VerifyingKey = parse_key(&self.author).map_err(|_| LedgerError::Field)?;
        let raw: [u8; 64] = hexutil::decode(&self.sig)
            .map_err(|_| LedgerError::Signature)?
            .try_into()
            .map_err(|_| LedgerError::Signature)?;
        key.verify_strict(
            &Self::signed_bytes(&self.author, self.index, &self.prev, self.ts, &self.addrs),
            &Signature::from_bytes(&raw),
        )
        .map_err(|_| LedgerError::Signature)
    }
}
