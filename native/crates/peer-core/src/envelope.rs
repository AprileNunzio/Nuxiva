use crate::error::{PeerError, PeerResult};
use crate::ident::check_id;
use crate::message::Message;
use ed25519_dalek::{Signature, Signer, SigningKey, VerifyingKey};
use nuxiva_node_core::hexutil;
use nuxiva_node_core::identity::parse_key;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use zeroize::Zeroizing;

pub const DOMAIN: &str = "nuxiva-peer-v1";
pub const MAX_PAYLOAD: usize = 16 * 1024;
pub const SKEW_MS: i64 = 60_000;
pub const MAX_TTL: u8 = 12;
pub const REPLAY_WINDOW: u64 = 64;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Envelope {
    pub from: String,
    pub seq: u64,
    pub ts: i64,
    pub ttl: u8,
    pub payload: String,
    pub sig: String,
}

pub struct PeerKey {
    key: SigningKey,
    id: String,
}

impl std::fmt::Debug for PeerKey {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("PeerKey")
            .field("id", &self.id)
            .finish_non_exhaustive()
    }
}

fn signed_bytes(from: &str, seq: u64, ts: i64, payload: &str) -> Vec<u8> {
    let digest = hexutil::encode(&Sha256::digest(payload.as_bytes()));
    format!("{DOMAIN}\n{from}\n{seq}\n{ts}\n{digest}").into_bytes()
}

impl PeerKey {
    pub fn generate() -> PeerResult<Self> {
        let mut seed = Zeroizing::new([0u8; 32]);
        getrandom::fill(seed.as_mut_slice()).map_err(|_| PeerError::Key)?;
        Self::from_seed(&seed)
    }

    pub fn from_seed(seed: &[u8; 32]) -> PeerResult<Self> {
        let key = SigningKey::from_bytes(seed);
        let id = hexutil::encode(key.verifying_key().as_bytes());
        check_id(&id)?;
        Ok(Self { key, id })
    }

    #[must_use]
    pub fn id(&self) -> &str {
        &self.id
    }

    pub fn seal(&self, seq: u64, ts: i64, ttl: u8, message: &Message) -> PeerResult<Envelope> {
        let payload = serde_json::to_string(message).map_err(|_| PeerError::Payload)?;
        if payload.len() > MAX_PAYLOAD || ttl > MAX_TTL {
            return Err(PeerError::Limit);
        }
        let sig = self.key.sign(&signed_bytes(&self.id, seq, ts, &payload));
        Ok(Envelope {
            from: self.id.clone(),
            seq,
            ts,
            ttl,
            payload,
            sig: hexutil::encode(&sig.to_bytes()),
        })
    }
}

impl Envelope {
    #[must_use]
    pub fn message_id(&self) -> String {
        let mut hasher = Sha256::new();
        hasher.update(self.from.as_bytes());
        hasher.update(self.seq.to_be_bytes());
        hasher.update(self.sig.as_bytes());
        hexutil::encode(&hasher.finalize())
    }

    #[must_use]
    pub fn hop(&self) -> Self {
        Self {
            ttl: self.ttl.saturating_sub(1),
            ..self.clone()
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct TrustBook {
    keys: BTreeMap<String, VerifyingKey>,
}

impl TrustBook {
    pub const MAX: usize = crate::registry::MAX_NODES;

    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn enroll(&mut self, id: &str) -> PeerResult<()> {
        let key = parse_key(id).map_err(|_| PeerError::Key)?;
        check_id(id)?;
        if !self.keys.contains_key(id) && self.keys.len() >= Self::MAX {
            return Err(PeerError::Capacity);
        }
        self.keys.insert(id.to_owned(), key);
        Ok(())
    }

    pub fn revoke(&mut self, id: &str) -> bool {
        self.keys.remove(id).is_some()
    }

    #[must_use]
    pub fn trusts(&self, id: &str) -> bool {
        self.keys.contains_key(id)
    }
}

#[derive(Debug, Clone, Copy, Default)]
struct Window {
    top: u64,
    seen: u64,
}

#[derive(Debug, Clone, Default)]
pub struct Verifier {
    trust: TrustBook,
    windows: BTreeMap<String, Window>,
}

impl Verifier {
    #[must_use]
    pub fn new(trust: TrustBook) -> Self {
        Self {
            trust,
            windows: BTreeMap::new(),
        }
    }

    pub fn trust_mut(&mut self) -> &mut TrustBook {
        &mut self.trust
    }

    #[must_use]
    pub fn trust(&self) -> &TrustBook {
        &self.trust
    }

    pub fn open(&mut self, envelope: &Envelope, now_ms: i64) -> PeerResult<Message> {
        if envelope.payload.len() > MAX_PAYLOAD || envelope.ttl > MAX_TTL {
            return Err(PeerError::Limit);
        }
        let key = self
            .trust
            .keys
            .get(&envelope.from)
            .ok_or(PeerError::Untrusted)?;
        if now_ms.abs_diff(envelope.ts) > SKEW_MS.unsigned_abs() {
            return Err(PeerError::Clock);
        }
        let raw: [u8; 64] = hexutil::decode(&envelope.sig)
            .map_err(|_| PeerError::Signature)?
            .try_into()
            .map_err(|_| PeerError::Signature)?;
        key.verify_strict(
            &signed_bytes(&envelope.from, envelope.seq, envelope.ts, &envelope.payload),
            &Signature::from_bytes(&raw),
        )
        .map_err(|_| PeerError::Signature)?;
        let message: Message =
            serde_json::from_str(&envelope.payload).map_err(|_| PeerError::Payload)?;
        let window = self.windows.entry(envelope.from.clone()).or_default();
        Self::admit(window, envelope.seq)?;
        Ok(message)
    }

    fn admit(window: &mut Window, seq: u64) -> PeerResult<()> {
        if seq == 0 {
            return Err(PeerError::Replay);
        }
        if seq > window.top {
            let shift = seq.saturating_sub(window.top);
            window.seen = if shift >= REPLAY_WINDOW {
                1
            } else {
                (window.seen << shift) | 1
            };
            window.top = seq;
            return Ok(());
        }
        let offset = window.top.saturating_sub(seq);
        if offset >= REPLAY_WINDOW {
            return Err(PeerError::Replay);
        }
        let bit = 1u64 << offset;
        if window.seen & bit != 0 {
            return Err(PeerError::Replay);
        }
        window.seen |= bit;
        Ok(())
    }
}
