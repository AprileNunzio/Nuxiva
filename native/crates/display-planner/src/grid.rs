use serde::{Deserialize, Serialize};

pub const COLS: u8 = 12;
pub const MIN_ROWS: u8 = 4;
pub const MAX_ROWS: u8 = 24;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Slot {
    pub col: u8,
    pub row: u8,
    pub w: u8,
    pub h: u8,
}

impl Slot {
    #[must_use]
    pub const fn area(self) -> u16 {
        (self.w as u16).saturating_mul(self.h as u16)
    }

    #[must_use]
    pub const fn overlaps(self, other: Self) -> bool {
        let (a_right, a_bottom) = (
            self.col.saturating_add(self.w),
            self.row.saturating_add(self.h),
        );
        let (b_right, b_bottom) = (
            other.col.saturating_add(other.w),
            other.row.saturating_add(other.h),
        );
        self.col < b_right && other.col < a_right && self.row < b_bottom && other.row < a_bottom
    }
}

#[must_use]
pub fn rows_for(aspect: f32) -> u8 {
    if !aspect.is_finite() || aspect <= 0.0 {
        return 7;
    }
    let raw = (f32::from(COLS) / aspect).round();
    if raw <= f32::from(MIN_ROWS) {
        MIN_ROWS
    } else if raw >= f32::from(MAX_ROWS) {
        MAX_ROWS
    } else {
        let mut rows = MIN_ROWS;
        while f32::from(rows) < raw && rows < MAX_ROWS {
            rows = rows.saturating_add(1);
        }
        rows
    }
}

#[derive(Debug, Clone)]
pub struct Grid {
    pub cols: u8,
    pub rows: u8,
    taken: Vec<Slot>,
}

impl Grid {
    #[must_use]
    pub const fn new(rows: u8) -> Self {
        Self {
            cols: COLS,
            rows,
            taken: Vec::new(),
        }
    }

    #[must_use]
    pub const fn inside(&self, slot: Slot) -> bool {
        slot.w > 0
            && slot.h > 0
            && slot.col.saturating_add(slot.w) <= self.cols
            && slot.row.saturating_add(slot.h) <= self.rows
    }

    #[must_use]
    pub fn free(&self, slot: Slot) -> bool {
        self.inside(slot) && !self.taken.iter().any(|t| t.overlaps(slot))
    }

    pub fn take(&mut self, slot: Slot) -> bool {
        if self.free(slot) {
            self.taken.push(slot);
            true
        } else {
            false
        }
    }

    #[must_use]
    pub fn used(&self) -> u16 {
        self.taken
            .iter()
            .fold(0_u16, |sum, s| sum.saturating_add(s.area()))
    }

    #[must_use]
    pub const fn total(&self) -> u16 {
        (self.cols as u16).saturating_mul(self.rows as u16)
    }

    fn touches(&self, slot: Slot) -> bool {
        let right = slot.col.saturating_add(slot.w);
        let bottom = slot.row.saturating_add(slot.h);
        let rows = |t: &Slot| t.row < bottom && slot.row < t.row.saturating_add(t.h);
        let cols = |t: &Slot| t.col < right && slot.col < t.col.saturating_add(t.w);
        let vertical = slot.row == 0
            || bottom == self.rows
            || self
                .taken
                .iter()
                .any(|t| cols(t) && (t.row.saturating_add(t.h) == slot.row || t.row == bottom));
        let horizontal = slot.col == 0
            || right == self.cols
            || self
                .taken
                .iter()
                .any(|t| rows(t) && (t.col.saturating_add(t.w) == slot.col || t.col == right));
        vertical && horizontal
    }

    #[must_use]
    pub fn fit(&self, w: u8, h: u8, anchor: (f32, f32)) -> Option<Slot> {
        let (w, h) = (w.min(self.cols), h.min(self.rows));
        let mut best: Option<(f32, Slot)> = None;
        for row in 0..=self.rows.saturating_sub(h) {
            for col in 0..=self.cols.saturating_sub(w) {
                let slot = Slot { col, row, w, h };
                if !self.free(slot) || !self.touches(slot) {
                    continue;
                }
                let cx = f32::from(col) + f32::from(w) / 2.0;
                let cy = f32::from(row) + f32::from(h) / 2.0;
                let d = (cx - anchor.0).powi(2) + (cy - anchor.1).powi(2);
                if best.is_none_or(|(bd, _)| d < bd) {
                    best = Some((d, slot));
                }
            }
        }
        best.map(|(_, s)| s)
    }
}
