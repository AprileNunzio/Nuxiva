use std::fmt;

use nuxiva_seal_core::{Fernet, SealError};
use zeroize::Zeroize;

use crate::speaker::{MAX_DIM, MAX_ROWS, VoiceBook, VoicePolicy, valid_slug};

pub const MIN_ENROLL_ROWS: usize = 3;
pub const HANGOVER_S: f64 = 8.0;
pub const SEAL_TTL_S: i64 = 60 * 60 * 24 * 365 * 5;
const MAGIC: &[u8; 5] = b"NXVP1";
const NEED_MATCHES: u32 = 2;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LockError {
    Consent,
    Slug,
    Rows,
    Seal,
    Format,
}

impl LockError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Consent => "ear.lock.consent",
            Self::Slug => "ear.lock.slug",
            Self::Rows => "ear.lock.rows",
            Self::Seal => "ear.lock.seal",
            Self::Format => "ear.lock.format",
        }
    }
}

impl fmt::Display for LockError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for LockError {}

impl From<SealError> for LockError {
    fn from(_: SealError) -> Self {
        Self::Seal
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct Decision {
    pub admit: bool,
    pub unlocked: bool,
    pub score: f32,
    pub reason: &'static str,
}

pub struct VoiceLock {
    book: VoiceBook,
    owner: Option<String>,
    rows: Vec<Vec<f32>>,
    streak: u32,
    last_ok: Option<f64>,
    hangover: f64,
}

impl fmt::Debug for VoiceLock {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("VoiceLock")
            .field("enrolled", &self.owner.is_some())
            .field("streak", &self.streak)
            .finish_non_exhaustive()
    }
}

impl Drop for VoiceLock {
    fn drop(&mut self) {
        self.rows.iter_mut().for_each(Zeroize::zeroize);
    }
}

impl VoiceLock {
    #[must_use]
    pub fn new(policy: VoicePolicy, hangover: f64) -> Self {
        let hangover = if hangover.is_finite() {
            hangover.clamp(0.5, 120.0)
        } else {
            HANGOVER_S
        };
        Self {
            book: VoiceBook::new(policy),
            owner: None,
            rows: Vec::new(),
            streak: 0,
            last_ok: None,
            hangover,
        }
    }

    #[must_use]
    pub fn enrolled(&self) -> bool {
        self.owner.is_some()
    }

    pub fn enroll(
        &mut self,
        slug: &str,
        rows: &[Vec<f32>],
        consent: bool,
    ) -> Result<(), LockError> {
        if !consent {
            return Err(LockError::Consent);
        }
        if !valid_slug(slug) {
            return Err(LockError::Slug);
        }
        if rows.len() < MIN_ENROLL_ROWS || rows.len() > MAX_ROWS {
            return Err(LockError::Rows);
        }
        if !self.book.set_person(slug, rows) {
            return Err(LockError::Rows);
        }
        self.rows.iter_mut().for_each(Zeroize::zeroize);
        self.rows = rows.to_vec();
        self.owner = Some(slug.to_owned());
        self.streak = 0;
        self.last_ok = None;
        Ok(())
    }

    pub fn revoke(&mut self) {
        if let Some(slug) = self.owner.take() {
            self.book.remove(&slug);
        }
        self.rows.iter_mut().for_each(Zeroize::zeroize);
        self.rows.clear();
        self.streak = 0;
        self.last_ok = None;
    }

    #[must_use]
    pub fn unlocked(&self, now: f64) -> bool {
        self.last_ok
            .is_some_and(|t| now >= t && now - t <= self.hangover)
    }

    pub fn observe(&mut self, probe: &[f32], now: f64) -> Decision {
        let Some(owner) = self.owner.as_deref() else {
            return Decision {
                admit: false,
                unlocked: false,
                score: 0.0,
                reason: "non registrata",
            };
        };
        let verdict = self.book.verdict(probe);
        let matched = verdict.slug.as_deref() == Some(owner);
        if matched {
            self.streak = self.streak.saturating_add(1);
            if self.streak >= NEED_MATCHES || self.unlocked(now) {
                self.last_ok = Some(now);
            }
        } else {
            self.streak = 0;
        }
        Decision {
            admit: matched && self.unlocked(now),
            unlocked: self.unlocked(now),
            score: verdict.score,
            reason: if matched { "ok" } else { verdict.reason },
        }
    }

    pub fn seal(&self, fernet: &Fernet, now: i64) -> Result<String, LockError> {
        let owner = self.owner.as_deref().ok_or(LockError::Rows)?;
        let dim = self.rows.first().map_or(0, Vec::len);
        let mut plain = Vec::with_capacity(
            MAGIC
                .len()
                .saturating_add(owner.len())
                .saturating_add(8)
                .saturating_add(self.rows.len().saturating_mul(dim).saturating_mul(4)),
        );
        plain.extend_from_slice(MAGIC);
        plain.push(u8::try_from(owner.len()).map_err(|_| LockError::Slug)?);
        plain.extend_from_slice(owner.as_bytes());
        plain.extend_from_slice(
            &u16::try_from(dim)
                .map_err(|_| LockError::Rows)?
                .to_le_bytes(),
        );
        plain.extend_from_slice(
            &u16::try_from(self.rows.len())
                .map_err(|_| LockError::Rows)?
                .to_le_bytes(),
        );
        self.rows
            .iter()
            .flatten()
            .for_each(|v| plain.extend_from_slice(&v.to_le_bytes()));
        let token = fernet.encrypt(&plain, now);
        plain.zeroize();
        Ok(token?)
    }

    pub fn unseal(
        &mut self,
        fernet: &Fernet,
        token: &str,
        now: i64,
        consent: bool,
    ) -> Result<(), LockError> {
        let mut plain = fernet.decrypt(token.as_bytes(), Some(SEAL_TTL_S), now)?;
        let parsed = parse(&plain);
        plain.zeroize();
        let (slug, rows) = parsed?;
        self.enroll(&slug, &rows, consent)
    }
}

fn take<'a>(data: &'a [u8], at: &mut usize, len: usize) -> Result<&'a [u8], LockError> {
    let end = at.checked_add(len).ok_or(LockError::Format)?;
    let out = data.get(*at..end).ok_or(LockError::Format)?;
    *at = end;
    Ok(out)
}

fn parse(data: &[u8]) -> Result<(String, Vec<Vec<f32>>), LockError> {
    let mut at = 0;
    if take(data, &mut at, MAGIC.len())? != MAGIC {
        return Err(LockError::Format);
    }
    let name = usize::from(*take(data, &mut at, 1)?.first().ok_or(LockError::Format)?);
    let slug = std::str::from_utf8(take(data, &mut at, name)?)
        .map_err(|_| LockError::Format)?
        .to_owned();
    let dim = take(data, &mut at, 2)?;
    let dim = usize::from(u16::from_le_bytes([
        *dim.first().ok_or(LockError::Format)?,
        *dim.get(1).ok_or(LockError::Format)?,
    ]));
    let count = take(data, &mut at, 2)?;
    let count = usize::from(u16::from_le_bytes([
        *count.first().ok_or(LockError::Format)?,
        *count.get(1).ok_or(LockError::Format)?,
    ]));
    if dim == 0 || dim > MAX_DIM || count > MAX_ROWS {
        return Err(LockError::Format);
    }
    let mut rows = Vec::with_capacity(count);
    for _ in 0..count {
        let raw = take(data, &mut at, dim.checked_mul(4).ok_or(LockError::Format)?)?;
        rows.push(
            raw.chunks_exact(4)
                .map(|c| {
                    f32::from_le_bytes([
                        c.first().copied().unwrap_or(0),
                        c.get(1).copied().unwrap_or(0),
                        c.get(2).copied().unwrap_or(0),
                        c.get(3).copied().unwrap_or(0),
                    ])
                })
                .collect(),
        );
    }
    Ok((slug, rows))
}
