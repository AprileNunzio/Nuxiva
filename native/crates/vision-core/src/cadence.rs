use crate::buffer::Source;

pub const THUMB_W: usize = 9;
pub const THUMB_H: usize = 8;
const SAME_BITS: u32 = 3;
const MIN_BASE_MS: u64 = 250;
const MAX_CEIL_MS: u64 = 120_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Verdict {
    Embed,
    NotDue,
    Unchanged,
}

#[derive(Debug, Clone, Copy, Default)]
struct Lane {
    last_at: Option<u64>,
    last_hash: Option<u64>,
    interval_ms: u64,
    unchanged: u32,
}

#[derive(Debug, Clone)]
pub struct Cadence {
    base_ms: u64,
    ceiling_ms: u64,
    lanes: [Lane; 2],
}

#[must_use]
pub fn dhash(thumb: &[u8]) -> Option<u64> {
    if thumb.len() != THUMB_W.saturating_mul(THUMB_H) {
        return None;
    }
    let mut bits = 0_u64;
    for (row, line) in thumb.chunks_exact(THUMB_W).enumerate() {
        for (col, pair) in line.windows(2).enumerate() {
            let (left, right) = (pair.first()?, pair.get(1)?);
            if left > right {
                let index = row.saturating_mul(THUMB_W - 1).saturating_add(col);
                bits |= 1_u64.checked_shl(u32::try_from(index).ok()?)?;
            }
        }
    }
    Some(bits)
}

const fn slot(source: Source) -> usize {
    match source {
        Source::Screen => 0,
        Source::Webcam => 1,
    }
}

impl Cadence {
    #[must_use]
    pub fn new(base_ms: u64, ceiling_ms: u64) -> Self {
        let base = base_ms.clamp(MIN_BASE_MS, MAX_CEIL_MS);
        let ceiling = ceiling_ms.clamp(base, MAX_CEIL_MS);
        let lane = Lane {
            interval_ms: base,
            ..Lane::default()
        };
        Self {
            base_ms: base,
            ceiling_ms: ceiling,
            lanes: [lane; 2],
        }
    }

    #[must_use]
    pub fn interval_ms(&self, source: Source) -> u64 {
        self.lanes
            .get(slot(source))
            .map_or(self.base_ms, |lane| lane.interval_ms)
    }

    #[must_use]
    pub fn due(&self, source: Source, now_ms: u64) -> bool {
        self.lanes.get(slot(source)).is_some_and(|lane| {
            lane.last_at
                .is_none_or(|at| now_ms.saturating_sub(at) >= lane.interval_ms)
        })
    }

    pub fn admit(&mut self, source: Source, hash: u64, now_ms: u64) -> Verdict {
        if !self.due(source, now_ms) {
            return Verdict::NotDue;
        }
        let (base, ceiling) = (self.base_ms, self.ceiling_ms);
        let Some(lane) = self.lanes.get_mut(slot(source)) else {
            return Verdict::NotDue;
        };
        lane.last_at = Some(now_ms);
        let same = lane
            .last_hash
            .is_some_and(|prev| (prev ^ hash).count_ones() <= SAME_BITS);
        lane.last_hash = Some(hash);
        if same {
            lane.unchanged = lane.unchanged.saturating_add(1);
            lane.interval_ms = lane
                .interval_ms
                .saturating_add(lane.interval_ms / 2)
                .min(ceiling);
            Verdict::Unchanged
        } else {
            lane.unchanged = 0;
            lane.interval_ms = base;
            Verdict::Embed
        }
    }

    pub fn reset(&mut self) {
        let base = self.base_ms;
        self.lanes = [Lane {
            interval_ms: base,
            ..Lane::default()
        }; 2];
    }

    #[must_use]
    pub fn unchanged_streak(&self, source: Source) -> u32 {
        self.lanes
            .get(slot(source))
            .map_or(0, |lane| lane.unchanged)
    }
}
