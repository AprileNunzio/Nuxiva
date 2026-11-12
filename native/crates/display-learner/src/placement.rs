use nuxiva_display_planner::Size;
use serde::{Deserialize, Serialize};

use crate::policy::{LearnerPolicy, decay};

pub const MAX_CELLS: usize = 32;
const SLACK: f32 = 1.0e-3;
const SIZES: [Size; 5] = [Size::S, Size::M, Size::L, Size::Xl, Size::Full];

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct Cell {
    pub col: u8,
    pub row: u8,
    pub weight: f32,
}

#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Placement {
    cells: Vec<Cell>,
    sizes: [f32; 5],
    at_ms: u64,
}

fn size_index(size: Size) -> usize {
    SIZES.iter().position(|s| *s == size).unwrap_or(1)
}

impl Placement {
    #[must_use]
    pub fn sane(&self) -> bool {
        self.cells.len() <= MAX_CELLS
            && self
                .cells
                .iter()
                .all(|c| c.col < 12 && c.row < 48 && c.weight.is_finite() && c.weight >= 0.0)
            && self.sizes.iter().all(|w| w.is_finite() && *w >= 0.0)
    }

    fn age(&mut self, now_ms: u64, policy: &LearnerPolicy) {
        let f = decay(now_ms.saturating_sub(self.at_ms), policy.half_life_ms);
        for c in &mut self.cells {
            c.weight *= f;
        }
        for w in &mut self.sizes {
            *w *= f;
        }
        self.cells.retain(|c| c.weight > 0.01);
        self.at_ms = self.at_ms.max(now_ms);
    }

    pub fn observe(
        &mut self,
        cell: Option<[u8; 2]>,
        size: Option<Size>,
        now_ms: u64,
        policy: &LearnerPolicy,
    ) {
        self.age(now_ms, policy);
        if let Some([col, row]) = cell {
            if let Some(hit) = self.cells.iter_mut().find(|c| c.col == col && c.row == row) {
                hit.weight += 1.0;
            } else {
                if self.cells.len() >= MAX_CELLS {
                    self.cells.sort_by(|a, b| b.weight.total_cmp(&a.weight));
                    self.cells.truncate(MAX_CELLS.saturating_sub(1));
                }
                self.cells.push(Cell {
                    col,
                    row,
                    weight: 1.0,
                });
            }
        }
        if let Some(w) = size.and_then(|s| self.sizes.get_mut(size_index(s))) {
            *w += 1.0;
        }
    }

    #[must_use]
    pub fn cell(&self, now_ms: u64, policy: &LearnerPolicy) -> Option<[u8; 2]> {
        let f = decay(now_ms.saturating_sub(self.at_ms), policy.half_life_ms);
        self.cells
            .iter()
            .filter(|c| c.weight * f >= policy.min_place_weight - SLACK)
            .max_by(|a, b| a.weight.total_cmp(&b.weight))
            .map(|c| [c.col, c.row])
    }

    #[must_use]
    pub fn size(&self, now_ms: u64, policy: &LearnerPolicy) -> Option<Size> {
        let f = decay(now_ms.saturating_sub(self.at_ms), policy.half_life_ms);
        self.sizes
            .iter()
            .zip(SIZES)
            .filter(|(w, _)| **w * f >= policy.min_place_weight - SLACK)
            .max_by(|a, b| a.0.total_cmp(b.0))
            .map(|(_, s)| s)
    }
}
