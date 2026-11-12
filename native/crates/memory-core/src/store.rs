use chacha20poly1305::XNonce;
use chacha20poly1305::aead::{Aead, Payload};
use nuxiva_sentinel_core::Day;
use nuxiva_sentinel_core::journal::{HASH_LEN, Head};
use nuxiva_sentinel_core::keys::{NONCE_LEN, cipher, random};

use crate::error::MemoryError;
use crate::index::{IndexKey, MAX_TOKENS, TOKEN_LEN, Token};
use crate::sighting::{Audience, Sighting};

pub const MAX_FRAME: usize = 32 * 1024;
pub const MAX_DAY: usize = 512 * 1024 * 1024;
const LEN_PREFIX: usize = 4;
const FIXED: usize = HASH_LEN + NONCE_LEN + 3;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Header {
    pub audience: Audience,
    pub pinned: bool,
    pub tokens: Vec<Token>,
}

#[derive(Debug, Clone)]
pub struct Frame<'a> {
    pub header: Header,
    prev: &'a [u8],
    nonce: &'a [u8],
    head_bytes: &'a [u8],
    ct: &'a [u8],
    body: &'a [u8],
}

const fn audience_byte(a: Audience) -> u8 {
    match a {
        Audience::Household => 1,
        Audience::Guest => 2,
        Audience::Passerby => 3,
        Audience::Object => 4,
    }
}

const fn audience_of(b: u8) -> Option<Audience> {
    match b {
        1 => Some(Audience::Household),
        2 => Some(Audience::Guest),
        3 => Some(Audience::Passerby),
        4 => Some(Audience::Object),
        _ => None,
    }
}

#[must_use]
pub fn genesis(day: &Day) -> Head {
    let mut h = blake3::Hasher::new();
    h.update(b"nuxiva.memory.genesis|");
    h.update(day.as_str().as_bytes());
    Head(*h.finalize().as_bytes())
}

fn aad(day: &Day, prev: &[u8], header: &[u8]) -> Vec<u8> {
    let mut out = b"memory.sighting|".to_vec();
    out.extend_from_slice(day.as_str().as_bytes());
    out.push(b'|');
    out.extend_from_slice(prev);
    out.push(b'|');
    out.extend_from_slice(header);
    out
}

fn encode_header(h: &Header) -> Result<Vec<u8>, MemoryError> {
    let count = u8::try_from(h.tokens.len()).map_err(|_| MemoryError::TooLarge)?;
    if h.tokens.len() > MAX_TOKENS {
        return Err(MemoryError::TooLarge);
    }
    let mut out = vec![audience_byte(h.audience), u8::from(h.pinned), count];
    for t in &h.tokens {
        out.extend_from_slice(t);
    }
    Ok(out)
}

pub fn seal(
    day_key: &[u8],
    day: &Day,
    prev: &Head,
    index: &IndexKey,
    sighting: &Sighting,
) -> Result<(Vec<u8>, Head), MemoryError> {
    sighting.validate()?;
    let header = encode_header(&Header {
        audience: sighting.audience(),
        pinned: sighting.pinned,
        tokens: index.of(sighting),
    })?;
    let plain = zeroize::Zeroizing::new(
        serde_json::to_vec(sighting).map_err(|_| MemoryError::InvalidSighting("json"))?,
    );
    let nonce = random::<NONCE_LEN>()?;
    let ct = cipher(day_key)?
        .encrypt(
            XNonce::from_slice(&nonce),
            Payload {
                msg: &plain,
                aad: &aad(day, &prev.0, &header),
            },
        )
        .map_err(|_| MemoryError::Crypto)?;
    let mut body = Vec::with_capacity(FIXED.saturating_add(header.len()).saturating_add(ct.len()));
    body.extend_from_slice(&prev.0);
    body.extend_from_slice(&nonce);
    body.extend_from_slice(&header);
    body.extend_from_slice(&ct);
    if body.len() > MAX_FRAME {
        return Err(MemoryError::TooLarge);
    }
    let len = u32::try_from(body.len()).map_err(|_| MemoryError::TooLarge)?;
    let head = Head(*blake3::hash(&body).as_bytes());
    let mut frame = len.to_be_bytes().to_vec();
    frame.extend_from_slice(&body);
    Ok((frame, head))
}

fn parse(body: &[u8], index: usize) -> Result<Frame<'_>, MemoryError> {
    let broken = MemoryError::Broken(index);
    let (prev, rest) = body.split_at_checked(HASH_LEN).ok_or(broken.clone())?;
    let (nonce, rest) = rest.split_at_checked(NONCE_LEN).ok_or(broken.clone())?;
    let (&[aud, pin, count], tail) = rest.split_first_chunk::<3>().ok_or(broken.clone())?;
    let audience = audience_of(aud).ok_or(broken.clone())?;
    if pin > 1 || usize::from(count) > MAX_TOKENS {
        return Err(broken);
    }
    let size = usize::from(count).saturating_mul(TOKEN_LEN);
    let (raw, ct) = tail.split_at_checked(size).ok_or(broken.clone())?;
    let tokens = raw
        .chunks_exact(TOKEN_LEN)
        .map(|c| {
            let mut t = [0_u8; TOKEN_LEN];
            t.copy_from_slice(c);
            t
        })
        .collect();
    let head_len = 3_usize.saturating_add(size);
    let head_bytes = rest.get(..head_len).ok_or(broken)?;
    Ok(Frame {
        header: Header {
            audience,
            pinned: pin == 1,
            tokens,
        },
        prev,
        nonce,
        head_bytes,
        ct,
        body,
    })
}

#[derive(Debug, Clone)]
pub struct Scan<'a> {
    pub frames: Vec<Frame<'a>>,
    pub head: Head,
    pub valid_len: usize,
    pub truncated: bool,
}

pub fn scan<'a>(day: &Day, data: &'a [u8]) -> Result<Scan<'a>, MemoryError> {
    if data.len() > MAX_DAY {
        return Err(MemoryError::TooLarge);
    }
    let mut frames = Vec::new();
    let mut head = genesis(day);
    let mut offset = 0_usize;
    let mut valid_len = 0_usize;
    loop {
        let rest = data.get(offset..).unwrap_or_default();
        if rest.is_empty() {
            return Ok(Scan {
                frames,
                head,
                valid_len,
                truncated: false,
            });
        }
        let Some((len, tail)) = rest.split_first_chunk::<LEN_PREFIX>() else {
            return Ok(Scan {
                frames,
                head,
                valid_len,
                truncated: true,
            });
        };
        let size = usize::try_from(u32::from_be_bytes(*len)).unwrap_or(usize::MAX);
        if !(FIXED..=MAX_FRAME).contains(&size) {
            return Err(MemoryError::Broken(frames.len()));
        }
        let Some(body) = tail.get(..size) else {
            return Ok(Scan {
                frames,
                head,
                valid_len,
                truncated: true,
            });
        };
        let frame = parse(body, frames.len())?;
        if frame.prev != head.0 {
            return Err(MemoryError::Broken(frames.len()));
        }
        head = Head(*blake3::hash(body).as_bytes());
        offset = offset.saturating_add(LEN_PREFIX).saturating_add(size);
        valid_len = offset;
        frames.push(frame);
    }
}

pub fn open(day_key: &[u8], day: &Day, frame: &Frame<'_>) -> Result<Sighting, MemoryError> {
    let plain = zeroize::Zeroizing::new(
        cipher(day_key)?
            .decrypt(
                XNonce::from_slice(frame.nonce),
                Payload {
                    msg: frame.ct,
                    aad: &aad(day, frame.prev, frame.head_bytes),
                },
            )
            .map_err(|_| MemoryError::Crypto)?,
    );
    let sighting: Sighting =
        serde_json::from_slice(&plain).map_err(|_| MemoryError::InvalidSighting("json"))?;
    sighting.validate()?;
    if sighting.audience() != frame.header.audience || sighting.pinned != frame.header.pinned {
        return Err(MemoryError::Crypto);
    }
    Ok(sighting)
}

pub fn open_all(day_key: &[u8], day: &Day, data: &[u8]) -> Result<Vec<Sighting>, MemoryError> {
    scan(day, data)?
        .frames
        .iter()
        .map(|f| open(day_key, day, f))
        .collect()
}

pub fn rewrite(
    day_key: &[u8],
    day: &Day,
    index: &IndexKey,
    sightings: &[Sighting],
) -> Result<(Vec<u8>, Head), MemoryError> {
    let mut head = genesis(day);
    let mut out = Vec::new();
    for s in sightings {
        let (frame, next) = seal(day_key, day, &head, index, s)?;
        out.extend_from_slice(&frame);
        head = next;
    }
    Ok((out, head))
}

impl Frame<'_> {
    #[must_use]
    pub fn body_len(&self) -> usize {
        self.body.len()
    }
}
