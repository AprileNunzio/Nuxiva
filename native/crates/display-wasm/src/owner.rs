use nuxiva_gesture_core::{Hand, Joint};
use serde::{Deserialize, Serialize};

pub const MAX_FACES: usize = 16;
const REACH_X: f32 = 3.0;
const REACH_UP: f32 = 1.0;
const REACH_DOWN: f32 = 6.0;
const MIN_WIDTH: f32 = 0.02;

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Face {
    pub x: f32,
    pub y: f32,
    pub w: f32,
    #[serde(default)]
    pub authorized: bool,
}

impl Face {
    #[must_use]
    pub fn sane(&self) -> bool {
        [self.x, self.y, self.w].iter().all(|v| v.is_finite())
            && (0.0..=1.0).contains(&self.x)
            && (0.0..=1.0).contains(&self.y)
            && self.w > 0.0
            && self.w <= 1.0
    }

    fn reach(&self, x: f32, y: f32) -> Option<f32> {
        let w = self.w.max(MIN_WIDTH);
        let dx = (x - self.x) / w;
        let dy = (y - self.y) / w;
        let inside = dx.abs() <= REACH_X && (-REACH_UP..=REACH_DOWN).contains(&dy);
        inside.then(|| dx.hypot(dy * 0.5))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Owner {
    Authorized,
    Guest,
    Unknown,
}

#[must_use]
pub fn owner_of(hand: &Hand, faces: &[Face]) -> Owner {
    let wrist = hand.at(Joint::Wrist);
    faces
        .iter()
        .filter(|f| f.sane())
        .take(MAX_FACES)
        .filter_map(|f| f.reach(wrist.x, wrist.y).map(|d| (d, f.authorized)))
        .min_by(|a, b| a.0.total_cmp(&b.0))
        .map_or(Owner::Unknown, |(_, authorized)| {
            if authorized {
                Owner::Authorized
            } else {
                Owner::Guest
            }
        })
}

#[must_use]
pub fn assign(hands: &[Hand], faces: &[Face]) -> Vec<Owner> {
    hands.iter().map(|h| owner_of(h, faces)).collect()
}
