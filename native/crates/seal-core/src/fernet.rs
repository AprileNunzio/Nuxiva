use aes::Aes128;
use aes::cipher::block_padding::Pkcs7;
use aes::cipher::{BlockDecryptMut, BlockEncryptMut, KeyIvInit};
use base64::Engine;
use base64::engine::general_purpose::URL_SAFE;
use hmac::{Hmac, Mac};
use sha2::Sha256;
use subtle::ConstantTimeEq;
use zeroize::{Zeroize, Zeroizing};

use crate::error::{SealError, SealResult};

pub const MAX_CLOCK_SKEW: i64 = 60;
pub const MAX_PLAINTEXT: usize = 256 * 1024 * 1024;
const VERSION: u8 = 0x80;
const HEADER: usize = 1 + 8 + 16;
const TAG: usize = 32;
const BLOCK: usize = 16;

type HmacSha256 = Hmac<Sha256>;
type Encryptor = cbc::Encryptor<Aes128>;
type Decryptor = cbc::Decryptor<Aes128>;

pub struct Fernet {
    signing: Zeroizing<[u8; 16]>,
    encryption: Zeroizing<[u8; 16]>,
}

impl std::fmt::Debug for Fernet {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Fernet").finish_non_exhaustive()
    }
}

fn random<const N: usize>() -> SealResult<[u8; N]> {
    let mut out = [0u8; N];
    getrandom::fill(&mut out).map_err(|_| SealError::Random)?;
    Ok(out)
}

pub fn generate_key() -> SealResult<String> {
    let mut raw = random::<32>()?;
    let key = URL_SAFE.encode(raw);
    raw.zeroize();
    Ok(key)
}

impl Fernet {
    pub fn new(key: &[u8]) -> SealResult<Self> {
        let text: Vec<u8> = key
            .iter()
            .copied()
            .filter(|b| !b.is_ascii_whitespace())
            .collect();
        let raw = Zeroizing::new(URL_SAFE.decode(&text).map_err(|_| SealError::Key)?);
        if raw.len() != 32 {
            return Err(SealError::Key);
        }
        let mut signing = Zeroizing::new([0u8; 16]);
        let mut encryption = Zeroizing::new([0u8; 16]);
        signing.copy_from_slice(raw.get(..16).ok_or(SealError::Key)?);
        encryption.copy_from_slice(raw.get(16..).ok_or(SealError::Key)?);
        Ok(Self {
            signing,
            encryption,
        })
    }

    fn mac(&self) -> SealResult<HmacSha256> {
        HmacSha256::new_from_slice(self.signing.as_slice()).map_err(|_| SealError::Key)
    }

    pub fn encrypt(&self, data: &[u8], now: i64) -> SealResult<String> {
        self.encrypt_with_iv(data, now, random::<16>()?)
    }

    pub fn encrypt_with_iv(&self, data: &[u8], now: i64, iv: [u8; 16]) -> SealResult<String> {
        if data.len() > MAX_PLAINTEXT {
            return Err(SealError::TooLarge);
        }
        let stamp = u64::try_from(now).map_err(|_| SealError::Token)?;
        let cipher = Encryptor::new(self.encryption.as_slice().into(), &iv.into())
            .encrypt_padded_vec_mut::<Pkcs7>(data);
        let mut token = Vec::with_capacity(HEADER.saturating_add(cipher.len()).saturating_add(TAG));
        token.push(VERSION);
        token.extend_from_slice(&stamp.to_be_bytes());
        token.extend_from_slice(&iv);
        token.extend_from_slice(&cipher);
        let mut mac = self.mac()?;
        mac.update(&token);
        token.extend_from_slice(&mac.finalize().into_bytes());
        Ok(URL_SAFE.encode(token))
    }

    pub fn decrypt(&self, token: &[u8], ttl: Option<i64>, now: i64) -> SealResult<Vec<u8>> {
        if token.len() > MAX_PLAINTEXT.saturating_mul(2) {
            return Err(SealError::TooLarge);
        }
        let data = URL_SAFE.decode(token).map_err(|_| SealError::Token)?;
        if data.first() != Some(&VERSION) {
            return Err(SealError::Token);
        }
        let stamp_bytes: [u8; 8] = data
            .get(1..9)
            .and_then(|s| s.try_into().ok())
            .ok_or(SealError::Token)?;
        let stamp = i64::try_from(u64::from_be_bytes(stamp_bytes)).map_err(|_| SealError::Token)?;
        if let Some(ttl) = ttl {
            if stamp.saturating_add(ttl) < now {
                return Err(SealError::Token);
            }
            if now.saturating_add(MAX_CLOCK_SKEW) < stamp {
                return Err(SealError::Token);
            }
        }
        let split = data.len().checked_sub(TAG).ok_or(SealError::Token)?;
        let body = data.get(..split).ok_or(SealError::Token)?;
        let tag = data.get(split..).ok_or(SealError::Token)?;
        let mut mac = self.mac()?;
        mac.update(body);
        let expected = mac.finalize().into_bytes();
        if !bool::from(expected.as_slice().ct_eq(tag)) {
            return Err(SealError::Token);
        }
        let iv: [u8; 16] = body
            .get(9..HEADER)
            .and_then(|s| s.try_into().ok())
            .ok_or(SealError::Token)?;
        let cipher = body.get(HEADER..).ok_or(SealError::Token)?;
        if cipher.is_empty() || cipher.len() % BLOCK != 0 {
            return Err(SealError::Token);
        }
        Decryptor::new(self.encryption.as_slice().into(), &iv.into())
            .decrypt_padded_vec_mut::<Pkcs7>(cipher)
            .map_err(|_| SealError::Token)
    }
}
