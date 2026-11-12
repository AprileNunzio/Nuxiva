use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{XChaCha20Poly1305, XNonce};
use hkdf::Hkdf;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use zeroize::Zeroizing;

use crate::crypto::{
    CHUNK_SIZE, KEY_LEN, NONCE_LEN, build_chunk_nonce, derive_day_camera_key, derive_segment_key,
};
use crate::error::{MediaVaultError, MediaVaultResult};

pub const MAGIC_V2: &[u8; 4] = b"NVM2";
pub const MAGIC_BLOB: &[u8; 4] = b"NVB1";
pub const TAG_LEN: usize = 16;
pub const FRAME_LEN: usize = 4 + CHUNK_SIZE + TAG_LEN;
pub const MAX_HEADER: usize = 4096;
pub const MAX_ID: usize = 64;
const AAD_DOMAIN: &[u8] = b"nuxiva.nvm2\0";
const BLOB_SALT: &[u8] = b"nuxiva.vault_media.blob.v1";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct HeaderV2 {
    pub v: u8,
    pub segment_id: String,
    pub camera_id: String,
    pub day: String,
    pub recorded_at_ms: u64,
    pub duration_ms: u32,
    pub has_audio: bool,
    pub has_video: bool,
    pub tier: String,
    pub plain_bytes: u64,
    pub chunk_count: u32,
    pub nonce: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SegmentSpec<'a> {
    pub segment_id: &'a str,
    pub camera_id: &'a str,
    pub day: &'a str,
    pub recorded_at_ms: u64,
    pub duration_ms: u32,
    pub has_audio: bool,
    pub has_video: bool,
    pub tier: &'a str,
}

#[must_use]
pub fn valid_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= MAX_ID
        && value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
}

#[must_use]
pub fn valid_day(value: &str) -> bool {
    let b = value.as_bytes();
    b.len() == 10
        && b.iter().enumerate().all(|(i, c)| {
            if i == 4 || i == 7 {
                *c == b'-'
            } else {
                c.is_ascii_digit()
            }
        })
}

#[must_use]
pub fn valid_tier(value: &str) -> bool {
    matches!(value, "continuous" | "event" | "pinned")
}

#[must_use]
pub fn chunk_count_for(plain_bytes: u64) -> u64 {
    plain_bytes.div_ceil(CHUNK_SIZE as u64).max(1)
}

fn hex(bytes: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len().saturating_mul(2));
    for b in bytes {
        out.push(char::from(
            *DIGITS.get(usize::from(b >> 4)).unwrap_or(&b'0'),
        ));
        out.push(char::from(
            *DIGITS.get(usize::from(b & 15)).unwrap_or(&b'0'),
        ));
    }
    out
}

fn unhex_nonce(text: &str) -> MediaVaultResult<[u8; NONCE_LEN]> {
    let raw = text.as_bytes();
    if raw.len() != NONCE_LEN.saturating_mul(2) {
        return Err(MediaVaultError::InvalidHeader);
    }
    let mut out = [0u8; NONCE_LEN];
    for (slot, pair) in out.iter_mut().zip(raw.chunks(2)) {
        let digit = |c: u8| -> MediaVaultResult<u8> {
            match c {
                b'0'..=b'9' => Ok(c.saturating_sub(b'0')),
                b'a'..=b'f' => Ok(c.saturating_sub(b'a').saturating_add(10)),
                _ => Err(MediaVaultError::InvalidHeader),
            }
        };
        let hi = digit(*pair.first().ok_or(MediaVaultError::InvalidHeader)?)?;
        let lo = digit(*pair.get(1).ok_or(MediaVaultError::InvalidHeader)?)?;
        *slot = (hi << 4) | lo;
    }
    Ok(out)
}

impl HeaderV2 {
    pub fn validate(&self) -> MediaVaultResult<()> {
        let chunks_ok = u64::from(self.chunk_count) == chunk_count_for(self.plain_bytes);
        if self.v != 2
            || !valid_id(&self.segment_id)
            || !valid_id(&self.camera_id)
            || !valid_day(&self.day)
            || !valid_tier(&self.tier)
            || !chunks_ok
        {
            return Err(MediaVaultError::InvalidHeader);
        }
        unhex_nonce(&self.nonce).map(|_| ())
    }

    pub fn base_nonce(&self) -> MediaVaultResult<[u8; NONCE_LEN]> {
        unhex_nonce(&self.nonce)
    }

    #[must_use]
    pub fn chunk_plain_len(&self, index: u64) -> usize {
        let start = index.saturating_mul(CHUNK_SIZE as u64);
        let left = self.plain_bytes.saturating_sub(start);
        usize::try_from(left.min(CHUNK_SIZE as u64)).unwrap_or(CHUNK_SIZE)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OpenedHeader {
    pub header: HeaderV2,
    pub raw: Vec<u8>,
    pub data_start: usize,
}

impl OpenedHeader {
    #[must_use]
    pub fn frame_offset(&self, index: u64) -> u64 {
        (self.data_start as u64).saturating_add(index.saturating_mul(FRAME_LEN as u64))
    }

    #[must_use]
    pub fn frame_len(&self, index: u64) -> usize {
        self.header
            .chunk_plain_len(index)
            .saturating_add(TAG_LEN)
            .saturating_add(4)
    }
}

pub fn parse_header(prefix: &[u8]) -> MediaVaultResult<OpenedHeader> {
    if prefix.get(..4) != Some(MAGIC_V2.as_slice()) {
        return Err(MediaVaultError::InvalidHeader);
    }
    let mut len = [0u8; 4];
    len.copy_from_slice(prefix.get(4..8).ok_or(MediaVaultError::InvalidHeader)?);
    let header_len = u32::from_be_bytes(len) as usize;
    if header_len == 0 || header_len > MAX_HEADER {
        return Err(MediaVaultError::InvalidHeader);
    }
    let data_start = 8usize.saturating_add(header_len);
    let raw = prefix
        .get(8..data_start)
        .ok_or(MediaVaultError::InvalidHeader)?
        .to_vec();
    let header: HeaderV2 =
        serde_json::from_slice(&raw).map_err(|_| MediaVaultError::InvalidHeader)?;
    header.validate()?;
    Ok(OpenedHeader {
        header,
        raw,
        data_start,
    })
}

#[must_use]
pub fn chunk_aad(header_raw: &[u8], index: u64, last: bool) -> Vec<u8> {
    let mut hasher = Sha256::new();
    hasher.update(AAD_DOMAIN);
    hasher.update(header_raw);
    let mut out = hasher.finalize().to_vec();
    out.extend_from_slice(&index.to_be_bytes());
    out.push(u8::from(last));
    out
}

fn segment_key(
    master: &[u8],
    camera_id: &str,
    day: &str,
    segment_id: &str,
) -> MediaVaultResult<Zeroizing<[u8; KEY_LEN]>> {
    let day_key = derive_day_camera_key(master, camera_id, day)?;
    derive_segment_key(&day_key, segment_id)
}

fn cipher(key: &[u8; KEY_LEN]) -> MediaVaultResult<XChaCha20Poly1305> {
    XChaCha20Poly1305::new_from_slice(key).map_err(|e| MediaVaultError::Crypto(e.to_string()))
}

pub fn seal_segment(
    master: &[u8],
    spec: &SegmentSpec<'_>,
    base_nonce: &[u8; NONCE_LEN],
    raw_media: &[u8],
) -> MediaVaultResult<Vec<u8>> {
    let plain_bytes = raw_media.len() as u64;
    let chunk_count = u32::try_from(chunk_count_for(plain_bytes))
        .map_err(|_| MediaVaultError::Serialization("segment too large".into()))?;
    let header = HeaderV2 {
        v: 2,
        segment_id: spec.segment_id.into(),
        camera_id: spec.camera_id.into(),
        day: spec.day.into(),
        recorded_at_ms: spec.recorded_at_ms,
        duration_ms: spec.duration_ms,
        has_audio: spec.has_audio,
        has_video: spec.has_video,
        tier: spec.tier.into(),
        plain_bytes,
        chunk_count,
        nonce: hex(base_nonce),
    };
    header.validate()?;
    let raw =
        serde_json::to_vec(&header).map_err(|e| MediaVaultError::Serialization(e.to_string()))?;
    if raw.len() > MAX_HEADER {
        return Err(MediaVaultError::InvalidHeader);
    }
    let header_len = u32::try_from(raw.len()).map_err(|_| MediaVaultError::InvalidHeader)?;
    let key = segment_key(master, spec.camera_id, spec.day, spec.segment_id)?;
    let engine = cipher(&key)?;
    let mut out = Vec::with_capacity(
        raw.len()
            .saturating_add(8)
            .saturating_add(raw_media.len())
            .saturating_add((chunk_count as usize).saturating_mul(TAG_LEN.saturating_add(4))),
    );
    out.extend_from_slice(MAGIC_V2);
    out.extend_from_slice(&header_len.to_be_bytes());
    out.extend_from_slice(&raw);
    let last_index = u64::from(chunk_count).saturating_sub(1);
    let mut pieces: Vec<&[u8]> = raw_media.chunks(CHUNK_SIZE).collect();
    if pieces.is_empty() {
        pieces.push(&[]);
    }
    for (index, piece) in (0u64..).zip(pieces) {
        let nonce = build_chunk_nonce(base_nonce, index);
        let aad = chunk_aad(&raw, index, index == last_index);
        let sealed = engine
            .encrypt(
                XNonce::from_slice(&nonce),
                Payload {
                    msg: piece,
                    aad: &aad,
                },
            )
            .map_err(|e| MediaVaultError::Crypto(e.to_string()))?;
        let len = u32::try_from(sealed.len()).map_err(|_| MediaVaultError::InvalidRange)?;
        out.extend_from_slice(&len.to_be_bytes());
        out.extend_from_slice(&sealed);
    }
    Ok(out)
}

pub fn open_chunk(
    master: &[u8],
    opened: &OpenedHeader,
    index: u64,
    frame: &[u8],
) -> MediaVaultResult<Vec<u8>> {
    let header = &opened.header;
    if index >= u64::from(header.chunk_count) {
        return Err(MediaVaultError::InvalidRange);
    }
    let mut len = [0u8; 4];
    len.copy_from_slice(frame.get(..4).ok_or(MediaVaultError::CorruptedPayload)?);
    let sealed_len = u32::from_be_bytes(len) as usize;
    let expected = header.chunk_plain_len(index).saturating_add(TAG_LEN);
    if sealed_len != expected {
        return Err(MediaVaultError::CorruptedPayload);
    }
    let sealed = frame
        .get(4..4usize.saturating_add(sealed_len))
        .ok_or(MediaVaultError::CorruptedPayload)?;
    let key = segment_key(master, &header.camera_id, &header.day, &header.segment_id)?;
    let nonce = build_chunk_nonce(&header.base_nonce()?, index);
    let last = index == u64::from(header.chunk_count).saturating_sub(1);
    let aad = chunk_aad(&opened.raw, index, last);
    cipher(&key)?
        .decrypt(
            XNonce::from_slice(&nonce),
            Payload {
                msg: sealed,
                aad: &aad,
            },
        )
        .map_err(|_| MediaVaultError::ChunkCorrupted)
}

pub fn open_segment(master: &[u8], bytes: &[u8]) -> MediaVaultResult<(HeaderV2, Vec<u8>)> {
    let opened = parse_header(bytes)?;
    let total = opened.frame_offset(u64::from(opened.header.chunk_count).saturating_sub(1));
    let end = usize::try_from(total)
        .map_err(|_| MediaVaultError::InvalidRange)?
        .saturating_add(opened.frame_len(u64::from(opened.header.chunk_count).saturating_sub(1)));
    if end != bytes.len() {
        return Err(MediaVaultError::CorruptedPayload);
    }
    let mut out = Vec::with_capacity(usize::try_from(opened.header.plain_bytes).unwrap_or(0));
    for index in 0..u64::from(opened.header.chunk_count) {
        let start = usize::try_from(opened.frame_offset(index))
            .map_err(|_| MediaVaultError::InvalidRange)?;
        let frame = bytes
            .get(start..start.saturating_add(opened.frame_len(index)))
            .ok_or(MediaVaultError::CorruptedPayload)?;
        out.extend_from_slice(&open_chunk(master, &opened, index, frame)?);
    }
    Ok((opened.header, out))
}

#[must_use]
pub fn chunk_span(plain_bytes: u64, start: u64, end_inclusive: u64) -> Option<(u64, u64)> {
    if plain_bytes == 0 || start > end_inclusive || start >= plain_bytes {
        return None;
    }
    let end = end_inclusive.min(plain_bytes.saturating_sub(1));
    let size = CHUNK_SIZE as u64;
    Some((start.checked_div(size)?, end.checked_div(size)?))
}

fn blob_key(master: &[u8], context: &str) -> MediaVaultResult<Zeroizing<[u8; KEY_LEN]>> {
    let hk = Hkdf::<Sha256>::new(Some(BLOB_SALT), master);
    let mut okm = Zeroizing::new([0u8; KEY_LEN]);
    hk.expand(context.as_bytes(), &mut *okm)
        .map_err(|_| MediaVaultError::KeyDerivation)?;
    Ok(okm)
}

pub fn seal_blob(
    master: &[u8],
    context: &str,
    nonce: &[u8; NONCE_LEN],
    plain: &[u8],
) -> MediaVaultResult<Vec<u8>> {
    if context.is_empty() || context.len() > 128 {
        return Err(MediaVaultError::InvalidHeader);
    }
    let key = blob_key(master, context)?;
    let sealed = cipher(&key)?
        .encrypt(
            XNonce::from_slice(nonce),
            Payload {
                msg: plain,
                aad: context.as_bytes(),
            },
        )
        .map_err(|e| MediaVaultError::Crypto(e.to_string()))?;
    let mut out = Vec::with_capacity(sealed.len().saturating_add(4 + NONCE_LEN));
    out.extend_from_slice(MAGIC_BLOB);
    out.extend_from_slice(nonce);
    out.extend_from_slice(&sealed);
    Ok(out)
}

pub fn open_blob(master: &[u8], context: &str, blob: &[u8]) -> MediaVaultResult<Vec<u8>> {
    if blob.get(..4) != Some(MAGIC_BLOB.as_slice()) {
        return Err(MediaVaultError::InvalidHeader);
    }
    let nonce = blob
        .get(4..4 + NONCE_LEN)
        .ok_or(MediaVaultError::CorruptedPayload)?;
    let sealed = blob
        .get(4 + NONCE_LEN..)
        .ok_or(MediaVaultError::CorruptedPayload)?;
    let key = blob_key(master, context)?;
    cipher(&key)?
        .decrypt(
            XNonce::from_slice(nonce),
            Payload {
                msg: sealed,
                aad: context.as_bytes(),
            },
        )
        .map_err(|_| MediaVaultError::ChunkCorrupted)
}
