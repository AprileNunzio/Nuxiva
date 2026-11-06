use nuxiva_sentinel_core::Day;
use nuxiva_sentinel_core::journal::Head;

use crate::error::MemoryError;
use crate::index::IndexKey;
use crate::retention::Policy;
use crate::sighting::{Sighting, Who};
use crate::store::{open, open_all, rewrite, scan};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Rewritten {
    pub data: Vec<u8>,
    pub head: Head,
    pub count: usize,
    pub changed: usize,
}

fn finish(
    day_key: &[u8],
    day: &Day,
    index: &IndexKey,
    kept: &[Sighting],
    changed: usize,
) -> Result<Rewritten, MemoryError> {
    let (data, head) = rewrite(day_key, day, index, kept)?;
    Ok(Rewritten {
        data,
        head,
        count: kept.len(),
        changed,
    })
}

pub fn erase(
    day_key: &[u8],
    day: &Day,
    index: &IndexKey,
    data: &[u8],
    who: &Who,
) -> Result<Option<Rewritten>, MemoryError> {
    let target = index.who(who);
    let scanned = scan(day, data)?;
    let hit = scanned
        .frames
        .iter()
        .filter(|f| f.header.tokens.contains(&target))
        .count();
    if hit == 0 {
        return Ok(None);
    }
    let mut kept = Vec::with_capacity(scanned.frames.len());
    let mut removed = 0_usize;
    for frame in &scanned.frames {
        let s = open(day_key, day, frame)?;
        if s.who == *who {
            removed = removed.saturating_add(1);
        } else {
            kept.push(s);
        }
    }
    finish(day_key, day, index, &kept, removed).map(Some)
}

pub fn relink(
    day_key: &[u8],
    day: &Day,
    index: &IndexKey,
    data: &[u8],
    from: &Who,
    to: &Who,
) -> Result<Option<Rewritten>, MemoryError> {
    if !to.valid() || *to == Who::Unknown || from == to {
        return Err(MemoryError::InvalidSighting("who"));
    }
    let target = index.who(from);
    let scanned = scan(day, data)?;
    if !scanned
        .frames
        .iter()
        .any(|f| f.header.tokens.contains(&target))
    {
        return Ok(None);
    }
    let mut all = open_all(day_key, day, data)?;
    let mut moved = 0_usize;
    for s in &mut all {
        if s.who == *from {
            s.who = to.clone();
            moved = moved.saturating_add(1);
        }
    }
    finish(day_key, day, index, &all, moved).map(Some)
}

pub fn compact(
    day_key: &[u8],
    day: &Day,
    index: &IndexKey,
    data: &[u8],
    policy: &Policy,
    age_days: u16,
) -> Result<Option<Rewritten>, MemoryError> {
    let scanned = scan(day, data)?;
    let expired = scanned
        .frames
        .iter()
        .filter(|f| !policy.keeps(&f.header, age_days))
        .count();
    if expired == 0 {
        return Ok(None);
    }
    let kept = scanned
        .frames
        .iter()
        .filter(|f| policy.keeps(&f.header, age_days))
        .map(|f| open(day_key, day, f))
        .collect::<Result<Vec<_>, _>>()?;
    finish(day_key, day, index, &kept, expired).map(Some)
}

pub fn pin(
    day_key: &[u8],
    day: &Day,
    index: &IndexKey,
    data: &[u8],
    id: &str,
    pinned: bool,
) -> Result<Option<Rewritten>, MemoryError> {
    let mut all = open_all(day_key, day, data)?;
    let mut changed = 0_usize;
    for s in &mut all {
        if s.id == id && s.pinned != pinned {
            s.pinned = pinned;
            changed = changed.saturating_add(1);
        }
    }
    if changed == 0 {
        return Ok(None);
    }
    finish(day_key, day, index, &all, changed).map(Some)
}
