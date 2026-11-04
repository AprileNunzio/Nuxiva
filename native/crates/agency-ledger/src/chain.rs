use hmac::{Hmac, Mac};
use serde_json::Value;
use sha2::Sha256;

use crate::entry::Entry;
use crate::error::LedgerError;
use crate::hex;
use crate::key::LedgerKey;

const DOMAIN: &[u8] = b"nuxiva-agency-ledger-v1";
const MAX_KIND: usize = 64;
pub const MAX_PAYLOAD: usize = 256 * 1024;

type HmacSha256 = Hmac<Sha256>;

#[derive(Debug)]
pub struct Chain {
    key: LedgerKey,
    head: [u8; 32],
    next_seq: u64,
}

fn valid_kind(kind: &str) -> bool {
    !kind.is_empty()
        && kind.len() <= MAX_KIND
        && kind
            .chars()
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || matches!(c, '.' | '_' | '-'))
}

fn mac_for(
    key: &LedgerKey,
    seq: u64,
    at_ms: u64,
    kind: &str,
    payload: &[u8],
    prev: &[u8; 32],
) -> Result<HmacSha256, LedgerError> {
    let mut mac = HmacSha256::new_from_slice(key.bytes()).map_err(|_| LedgerError::InvalidKind)?;
    let kind_len = u64::try_from(kind.len()).map_err(|_| LedgerError::InvalidKind)?;
    let payload_len =
        u64::try_from(payload.len()).map_err(|_| LedgerError::PayloadTooLarge(MAX_PAYLOAD))?;
    mac.update(DOMAIN);
    mac.update(&seq.to_be_bytes());
    mac.update(&at_ms.to_be_bytes());
    mac.update(&kind_len.to_be_bytes());
    mac.update(kind.as_bytes());
    mac.update(&payload_len.to_be_bytes());
    mac.update(payload);
    mac.update(prev);
    Ok(mac)
}

impl Chain {
    #[must_use]
    pub fn new(key: LedgerKey) -> Self {
        Self {
            key,
            head: [0u8; 32],
            next_seq: 0,
        }
    }

    #[must_use]
    pub fn len(&self) -> u64 {
        self.next_seq
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.next_seq == 0
    }

    #[must_use]
    pub fn head(&self) -> String {
        hex::encode(&self.head)
    }

    pub fn seal(&mut self, kind: &str, payload: Value, at_ms: u64) -> Result<Entry, LedgerError> {
        if !valid_kind(kind) {
            return Err(LedgerError::InvalidKind);
        }
        let bytes = serde_json::to_vec(&payload)?;
        if bytes.len() > MAX_PAYLOAD {
            return Err(LedgerError::PayloadTooLarge(MAX_PAYLOAD));
        }
        let seq = self.next_seq;
        let following = seq.checked_add(1).ok_or(LedgerError::Exhausted)?;
        let tag: [u8; 32] = mac_for(&self.key, seq, at_ms, kind, &bytes, &self.head)?
            .finalize()
            .into_bytes()
            .into();
        let entry = Entry {
            seq,
            at_ms,
            kind: kind.to_owned(),
            payload,
            prev: hex::encode(&self.head),
            mac: hex::encode(&tag),
        };
        self.head = tag;
        self.next_seq = following;
        Ok(entry)
    }

    pub fn accept(&mut self, entry: &Entry) -> Result<(), LedgerError> {
        if entry.seq != self.next_seq {
            return Err(LedgerError::Sequence(entry.seq));
        }
        if !valid_kind(&entry.kind) {
            return Err(LedgerError::InvalidKind);
        }
        let prev = hex::decode(&entry.prev).ok_or(LedgerError::Link(entry.seq))?;
        if prev != self.head {
            return Err(LedgerError::Link(entry.seq));
        }
        let tag = hex::decode(&entry.mac).ok_or(LedgerError::Signature(entry.seq))?;
        let bytes = serde_json::to_vec(&entry.payload)?;
        if bytes.len() > MAX_PAYLOAD {
            return Err(LedgerError::PayloadTooLarge(MAX_PAYLOAD));
        }
        mac_for(
            &self.key,
            entry.seq,
            entry.at_ms,
            &entry.kind,
            &bytes,
            &prev,
        )?
        .verify_slice(&tag)
        .map_err(|_| LedgerError::Signature(entry.seq))?;
        self.next_seq = entry.seq.checked_add(1).ok_or(LedgerError::Exhausted)?;
        self.head = tag;
        Ok(())
    }
}
