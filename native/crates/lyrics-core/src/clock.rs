pub const JUMP_MS: i64 = 3_000;
pub const MAX_OBSERVATIONS: u32 = 3;
const MAX_ABS_MS: i64 = 1 << 50;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ClockReading {
    pub origin_ms: i64,
    pub jumped: bool,
    pub correction_ms: i64,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct SongClock {
    origin: Option<i64>,
    pending: Option<i64>,
    count: u32,
}

fn div_trunc(value: i64, by: i64) -> i64 {
    value.checked_div(by).unwrap_or(0)
}

impl SongClock {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    #[must_use]
    pub fn origin(&self) -> Option<i64> {
        self.origin
    }

    pub fn reset(&mut self) {
        *self = Self::default();
    }

    #[must_use]
    pub fn position(&self, now_ms: i64) -> Option<i64> {
        self.origin.map(|o| now_ms.saturating_sub(o))
    }

    pub fn observe(&mut self, wall_ms: i64, pos_ms: i64) -> ClockReading {
        let candidate = wall_ms
            .clamp(-MAX_ABS_MS, MAX_ABS_MS)
            .saturating_sub(pos_ms.clamp(-MAX_ABS_MS, MAX_ABS_MS));
        let Some(origin) = self.origin else {
            self.origin = Some(candidate);
            self.count = 1;
            self.pending = None;
            return ClockReading {
                origin_ms: candidate,
                jumped: true,
                correction_ms: 0,
            };
        };
        let error = candidate.saturating_sub(origin);
        if error.abs() <= JUMP_MS {
            let weight = i64::from(self.count.min(MAX_OBSERVATIONS)).saturating_add(1);
            let step = div_trunc(error, weight);
            let next = origin.saturating_add(step);
            self.origin = Some(next);
            self.count = self.count.saturating_add(1).min(MAX_OBSERVATIONS);
            self.pending = None;
            return ClockReading {
                origin_ms: next,
                jumped: false,
                correction_ms: step,
            };
        }
        if let Some(previous) = self.pending
            && candidate.saturating_sub(previous).abs() <= JUMP_MS
        {
            let next = previous.saturating_add(div_trunc(candidate.saturating_sub(previous), 2));
            self.origin = Some(next);
            self.count = 2;
            self.pending = None;
            return ClockReading {
                origin_ms: next,
                jumped: true,
                correction_ms: next.saturating_sub(origin),
            };
        }
        self.pending = Some(candidate);
        ClockReading {
            origin_ms: origin,
            jumped: false,
            correction_ms: 0,
        }
    }
}
