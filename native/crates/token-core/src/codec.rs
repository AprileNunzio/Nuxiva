use base64::Engine;
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use hmac::{Hmac, Mac};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use sha2::Sha256;
use zeroize::Zeroizing;

use crate::error::{TokenError, TokenResult};

type HmacSha256 = Hmac<Sha256>;

pub const PREFIX: &str = "v1.local.";
pub const MAX_TOKEN: usize = 8192;
pub const MAX_CLAIMS: usize = 4096;
pub const MAX_SUBJECT: usize = 256;
pub const MIN_SECRET: usize = 32;
pub const MAX_TTL: i64 = 30 * 24 * 3600;
pub const SKEW: i64 = 60;
const SIGNATURE_CHARS: usize = 43;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Payload {
    pub sub: String,
    pub iat: i64,
    pub exp: i64,
    pub claims: Map<String, Value>,
}

pub struct TokenCodec {
    secret: Zeroizing<Vec<u8>>,
}

impl std::fmt::Debug for TokenCodec {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("TokenCodec").finish_non_exhaustive()
    }
}

fn valid_subject(subject: &str) -> TokenResult<()> {
    let length = subject.chars().count();
    if length == 0 || length > MAX_SUBJECT || subject.chars().any(char::is_control) {
        return Err(TokenError::Subject);
    }
    Ok(())
}

impl TokenCodec {
    pub fn new(secret: &[u8]) -> TokenResult<Self> {
        if secret.len() < MIN_SECRET
            || secret
                .iter()
                .all(|byte| *byte == secret.first().copied().unwrap_or(0))
        {
            return Err(TokenError::WeakSecret);
        }
        Ok(Self {
            secret: Zeroizing::new(secret.to_vec()),
        })
    }

    fn sign(&self, body: &str) -> TokenResult<HmacSha256> {
        let mut mac =
            HmacSha256::new_from_slice(&self.secret).map_err(|_| TokenError::WeakSecret)?;
        mac.update(body.as_bytes());
        Ok(mac)
    }

    pub fn issue(
        &self,
        subject: &str,
        claims: Map<String, Value>,
        now: i64,
        ttl: i64,
    ) -> TokenResult<String> {
        valid_subject(subject)?;
        if ttl <= 0 || ttl > MAX_TTL {
            return Err(TokenError::Lifetime);
        }
        let exp = now.checked_add(ttl).ok_or(TokenError::Lifetime)?;
        let encoded_claims = serde_json::to_vec(&claims).map_err(|_| TokenError::Claims)?;
        if encoded_claims.len() > MAX_CLAIMS {
            return Err(TokenError::Claims);
        }
        let payload = Payload {
            sub: subject.to_owned(),
            iat: now,
            exp,
            claims,
        };
        let raw = serde_json::to_vec(&payload).map_err(|_| TokenError::Payload)?;
        let body = URL_SAFE_NO_PAD.encode(raw);
        let signature = URL_SAFE_NO_PAD.encode(self.sign(&body)?.finalize().into_bytes());
        let token = format!("{PREFIX}{body}.{signature}");
        if token.len() > MAX_TOKEN {
            return Err(TokenError::TooLarge);
        }
        Ok(token)
    }

    pub fn verify(&self, token: &str, now: i64) -> TokenResult<Payload> {
        if token.len() > MAX_TOKEN {
            return Err(TokenError::TooLarge);
        }
        let rest = token.strip_prefix(PREFIX).ok_or(TokenError::Format)?;
        let (body, signature) = rest.split_once('.').ok_or(TokenError::Format)?;
        if body.is_empty() || signature.len() != SIGNATURE_CHARS {
            return Err(TokenError::Format);
        }
        let expected = URL_SAFE_NO_PAD
            .decode(signature)
            .map_err(|_| TokenError::Format)?;
        self.sign(body)?
            .verify_slice(&expected)
            .map_err(|_| TokenError::Signature)?;
        let raw = URL_SAFE_NO_PAD
            .decode(body)
            .map_err(|_| TokenError::Format)?;
        let payload: Payload = serde_json::from_slice(&raw).map_err(|_| TokenError::Payload)?;
        valid_subject(&payload.sub)?;
        if payload.exp < payload.iat {
            return Err(TokenError::Payload);
        }
        if payload.exp < now {
            return Err(TokenError::Expired);
        }
        if payload.iat > now.saturating_add(SKEW) {
            return Err(TokenError::NotYetValid);
        }
        Ok(payload)
    }
}
