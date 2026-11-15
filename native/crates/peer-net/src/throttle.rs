use std::collections::BTreeMap;
use std::net::IpAddr;

pub const MAX_SOURCES: usize = 1024;

#[derive(Debug, Clone)]
pub struct Throttle {
    per_window: u32,
    window_ms: i64,
    seen: BTreeMap<IpAddr, (i64, u32)>,
}

impl Throttle {
    #[must_use]
    pub fn new(per_window: u32, window_ms: i64) -> Self {
        Self {
            per_window,
            window_ms,
            seen: BTreeMap::new(),
        }
    }

    pub fn allow(&mut self, source: IpAddr, now: i64) -> bool {
        if self.seen.len() >= MAX_SOURCES && !self.seen.contains_key(&source) {
            self.seen
                .retain(|_, (start, _)| now.saturating_sub(*start) < self.window_ms);
            if self.seen.len() >= MAX_SOURCES {
                return false;
            }
        }
        let slot = self.seen.entry(source).or_insert((now, 0));
        if now.saturating_sub(slot.0) >= self.window_ms {
            *slot = (now, 0);
        }
        slot.1 = slot.1.saturating_add(1);
        slot.1 <= self.per_window
    }
}
