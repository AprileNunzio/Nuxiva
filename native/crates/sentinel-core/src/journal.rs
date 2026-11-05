use chacha20poly1305::XNonce;
use chacha20poly1305::aead::{Aead, Payload};
use serde::Serialize;

use crate::error::SentinelError;
use crate::event::Event;
use crate::keys::{NONCE_LEN, cipher, random};

pub const HASH_LEN: usize = 32;
pub const MAX_FRAME: usize = 64 * 1024;
pub const MAX_DAY: usize = 256 * 1024 * 1024;
const LEN_PREFIX: usize = 4;
const BODY_HEADER: usize = HASH_LEN + NONCE_LEN;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Day(String);

impl Day {
    pub fn parse(raw: &str) -> Result<Self, SentinelError> {
        let b = raw.as_bytes();
        let shape = b.len() == 10
            && b.iter().enumerate().all(|(i, c)| {
                if i == 4 || i == 7 {
                    *c == b'-'
                } else {
                    c.is_ascii_digit()
                }
            });
        if !shape {
            return Err(SentinelError::InvalidDay);
        }
        let month = raw
            .get(5..7)
            .and_then(|m| m.parse::<u8>().ok())
            .unwrap_or(0);
        let day = raw
            .get(8..10)
            .and_then(|d| d.parse::<u8>().ok())
            .unwrap_or(0);
        if !(1..=12).contains(&month) || !(1..=31).contains(&day) {
            return Err(SentinelError::InvalidDay);
        }
        Ok(Self(raw.to_owned()))
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Head(pub [u8; HASH_LEN]);

impl Head {
    #[must_use]
    pub fn genesis(day: &Day) -> Self {
        let mut h = blake3::Hasher::new();
        h.update(b"nuxiva.sentinel.genesis|");
        h.update(day.as_str().as_bytes());
        Self(*h.finalize().as_bytes())
    }

    #[must_use]
    pub fn hex(&self) -> String {
        self.0.iter().fold(
            String::with_capacity(HASH_LEN.saturating_mul(2)),
            |mut out, b| {
                use std::fmt::Write as _;
                let _ = write!(out, "{b:02x}");
                out
            },
        )
    }

    pub fn from_hex(raw: &str) -> Result<Self, SentinelError> {
        if raw.len() != HASH_LEN.saturating_mul(2) {
            return Err(SentinelError::InvalidKey);
        }
        let mut out = [0_u8; HASH_LEN];
        for (slot, pair) in out.iter_mut().zip(raw.as_bytes().chunks(2)) {
            let text = std::str::from_utf8(pair).map_err(|_| SentinelError::InvalidKey)?;
            *slot = u8::from_str_radix(text, 16).map_err(|_| SentinelError::InvalidKey)?;
        }
        Ok(Self(out))
    }
}

fn aad(day: &Day, prev: &Head) -> Vec<u8> {
    let mut out = b"sentinel.event|".to_vec();
    out.extend_from_slice(day.as_str().as_bytes());
    out.push(b'|');
    out.extend_from_slice(&prev.0);
    out
}

pub fn append(
    day_key: &[u8],
    day: &Day,
    prev: &Head,
    event: &Event,
) -> Result<(Vec<u8>, Head), SentinelError> {
    event.validate()?;
    let plain = zeroize::Zeroizing::new(
        serde_json::to_vec(event).map_err(|_| SentinelError::InvalidEvent("json"))?,
    );
    let nonce = random::<NONCE_LEN>()?;
    let ct = cipher(day_key)?
        .encrypt(
            XNonce::from_slice(&nonce),
            Payload {
                msg: &plain,
                aad: &aad(day, prev),
            },
        )
        .map_err(|_| SentinelError::Crypto)?;
    let mut body = Vec::with_capacity(BODY_HEADER.saturating_add(ct.len()));
    body.extend_from_slice(&prev.0);
    body.extend_from_slice(&nonce);
    body.extend_from_slice(&ct);
    if body.len() > MAX_FRAME {
        return Err(SentinelError::TooLarge);
    }
    let len = u32::try_from(body.len()).map_err(|_| SentinelError::TooLarge)?;
    let head = Head(*blake3::hash(&body).as_bytes());
    let mut frame = len.to_be_bytes().to_vec();
    frame.extend_from_slice(&body);
    Ok((frame, head))
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Opened {
    pub events: Vec<Event>,
    pub head: String,
    pub count: usize,
    pub valid_len: usize,
    pub truncated: bool,
}

struct Frame<'a> {
    prev: &'a [u8],
    nonce: &'a [u8],
    ct: &'a [u8],
    body: &'a [u8],
}

fn frames(data: &[u8]) -> Result<(Vec<(usize, Frame<'_>)>, bool), SentinelError> {
    let mut out = Vec::new();
    let mut offset = 0_usize;
    loop {
        let Some(rest) = data.get(offset..) else {
            return Ok((out, true));
        };
        if rest.is_empty() {
            return Ok((out, false));
        }
        let Some((len, tail)) = rest.split_at_checked(LEN_PREFIX) else {
            return Ok((out, true));
        };
        let mut prefix = [0_u8; LEN_PREFIX];
        prefix.copy_from_slice(len);
        let size = usize::try_from(u32::from_be_bytes(prefix)).unwrap_or(usize::MAX);
        if !(BODY_HEADER..=MAX_FRAME).contains(&size) {
            return Err(SentinelError::Broken(out.len()));
        }
        let Some(body) = tail.get(..size) else {
            return Ok((out, true));
        };
        let (prev, after) = body.split_at(HASH_LEN.min(body.len()));
        let (nonce, ct) = after.split_at(NONCE_LEN.min(after.len()));
        offset = offset.saturating_add(LEN_PREFIX).saturating_add(size);
        out.push((
            offset,
            Frame {
                prev,
                nonce,
                ct,
                body,
            },
        ));
    }
}

pub fn verify(day: &Day, data: &[u8]) -> Result<(Head, usize, usize, bool), SentinelError> {
    if data.len() > MAX_DAY {
        return Err(SentinelError::TooLarge);
    }
    let (list, truncated) = frames(data)?;
    let mut head = Head::genesis(day);
    let mut valid = 0;
    for (index, (end, frame)) in list.iter().enumerate() {
        if frame.prev != head.0 {
            return Err(SentinelError::Broken(index));
        }
        head = Head(*blake3::hash(frame.body).as_bytes());
        valid = *end;
    }
    Ok((head, list.len(), valid, truncated))
}

pub fn open(day_key: &[u8], day: &Day, data: &[u8]) -> Result<Opened, SentinelError> {
    verify(day, data)?;
    let (list, truncated) = frames(data)?;
    let aead = cipher(day_key)?;
    let mut head = Head::genesis(day);
    let mut events = Vec::with_capacity(list.len());
    let mut valid_len = 0;
    for (index, (end, frame)) in list.iter().enumerate() {
        let plain = zeroize::Zeroizing::new(
            aead.decrypt(
                XNonce::from_slice(frame.nonce),
                Payload {
                    msg: frame.ct,
                    aad: &aad(day, &head),
                },
            )
            .map_err(|_| SentinelError::Broken(index))?,
        );
        let event: Event =
            serde_json::from_slice(&plain).map_err(|_| SentinelError::Broken(index))?;
        event.validate().map_err(|_| SentinelError::Broken(index))?;
        events.push(event);
        head = Head(*blake3::hash(frame.body).as_bytes());
        valid_len = *end;
    }
    Ok(Opened {
        count: events.len(),
        events,
        head: head.hex(),
        valid_len,
        truncated,
    })
}
