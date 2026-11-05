use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Cadence {
    Realtime,
    Live,
    Fresh,
    Slow,
    Static,
}

impl Cadence {
    #[must_use]
    pub const fn period_ms(self, live: bool) -> Option<u64> {
        match (self, live) {
            (Self::Live, true) => Some(1_000),
            (Self::Live, false) => Some(10_000),
            (Self::Fresh, true) => Some(5_000),
            (Self::Fresh, false) => Some(60_000),
            (Self::Slow, true) => Some(300_000),
            (Self::Slow, false) => Some(900_000),
            (Self::Realtime | Self::Static, _) => None,
        }
    }

    #[must_use]
    pub fn infer(refresh_seconds: Option<f64>) -> Self {
        match refresh_seconds {
            None => Self::Static,
            Some(s) if !s.is_finite() || s <= 0.0 => Self::Static,
            Some(s) if s < 1.0 => Self::Realtime,
            Some(s) if s <= 2.0 => Self::Live,
            Some(s) if s <= 60.0 => Self::Fresh,
            Some(_) => Self::Slow,
        }
    }
}
