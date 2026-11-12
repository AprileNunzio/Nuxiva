use crate::grid::{Grid, Slot};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Form {
    CoreHero,
    FloatingOrb,
    AmbientStream,
    WhisperPill,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Nucleus {
    pub form: Form,
    pub slot: Option<Slot>,
}

#[must_use]
pub fn hero(grid: &Grid) -> Slot {
    let (w, h) = (4_u8, 3_u8.min(grid.rows));
    Slot {
        col: grid.cols.saturating_sub(w) / 2,
        row: grid.rows.saturating_sub(h) / 2,
        w,
        h,
    }
}

#[must_use]
pub fn stream(grid: &Grid) -> Slot {
    Slot {
        col: 0,
        row: grid.rows.saturating_sub(1),
        w: grid.cols,
        h: 1,
    }
}

#[must_use]
pub fn orb(grid: &Grid) -> Option<Slot> {
    grid.fit(
        2,
        2,
        (f32::from(grid.cols) / 2.0, f32::from(grid.rows) / 2.0),
    )
}
