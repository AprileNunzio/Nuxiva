use base64::Engine;
use base64::engine::general_purpose::URL_SAFE;
use hmac::{Hmac, Mac};
use sha2::Sha256;
use subtle::ConstantTimeEq;
use zeroize::Zeroizing;

use crate::error::{GuardError, GuardResult};

pub const SESSION_TTL: i64 = 12 * 3600;
pub const MIN_SECRET: usize = 16;
pub const MAX_TOKEN: usize = 4096;
pub const MAX_USERNAME: usize = 256;
const MAX_LIFETIME: i64 = 31 * 24 * 3600;

type HmacSha256 = Hmac<Sha256>;

pub struct SessionCodec {
    secret: Zeroizing<Vec<u8>>,
}

impl std::fmt::Debug for SessionCodec {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SessionCodec").finish_non_exhaustive()
    }
}

fn to_hex(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len().saturating_mul(2));
    for byte in bytes {
        for nibble in [byte >> 4, byte & 0x0f] {
            out.push(HEX.get(usize::from(nibble)).map_or('0', |b| char::from(*b)));
        }
    }
    out
}

impl SessionCodec {
    pub fn new(secret: &[u8]) -> GuardResult<Self> {
        if secret.len() < MIN_SECRET {
            return Err(GuardError::WeakSecret);
        }
        Ok(Self {
            secret: Zeroizing::new(secret.to_vec()),
        })
    }

    fn signature(&self, payload: &str) -> GuardResult<String> {
        let mut mac =
            HmacSha256::new_from_slice(&self.secret).map_err(|_| GuardError::WeakSecret)?;
        mac.update(payload.as_bytes());
        Ok(to_hex(&mac.finalize().into_bytes()))
    }

    pub fn issue(&self, username: &str, now: i64, ttl: i64) -> GuardResult<String> {
        if username.is_empty() || username.len() > MAX_USERNAME || username.contains('\0') {
            return Err(GuardError::Username);
        }
        if !(1..=MAX_LIFETIME).contains(&ttl) {
            return Err(GuardError::Lifetime);
        }
        let expires = now.checked_add(ttl).ok_or(GuardError::Lifetime)?;
        let payload = format!("{username}|{expires}");
        let sig = self.signature(&payload)?;
        Ok(URL_SAFE.encode(format!("{payload}|{sig}")))
    }

    #[must_use]
    pub fn verify(&self, token: &str, now: f64) -> Option<String> {
        if token.is_empty() || token.len() > MAX_TOKEN {
            return None;
        }
        let raw = URL_SAFE.decode(token.as_bytes()).ok()?;
        let text = String::from_utf8(raw).ok()?;
        let mut parts = text.rsplitn(3, '|');
        let sig = parts.next()?;
        let expires = parts.next()?;
        let username = parts.next()?;
        if expires.is_empty() || !expires.bytes().all(|b| b.is_ascii_digit()) {
            return None;
        }
        let expected = self.signature(&format!("{username}|{expires}")).ok()?;
        if !bool::from(sig.as_bytes().ct_eq(expected.as_bytes())) {
            return None;
        }
        let expires: u64 = expires.parse().ok()?;
        #[allow(clippy::cast_precision_loss)]
        let deadline = expires as f64;
        if deadline < now {
            return None;
        }
        Some(username.to_owned())
    }
}
