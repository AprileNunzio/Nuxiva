use crate::error::GestureError;
use serde::{Deserialize, Serialize};

pub const LANDMARKS: usize = 21;
pub const MAX_HANDS: usize = 4;
const COORD_MIN: f32 = -0.5;
const COORD_MAX: f32 = 1.5;

#[derive(Debug, Clone, Copy, PartialEq, Default, Serialize, Deserialize)]
pub struct Point {
    pub x: f32,
    pub y: f32,
    #[serde(default)]
    pub z: f32,
}

impl Point {
    #[must_use]
    pub const fn new(x: f32, y: f32) -> Self {
        Self { x, y, z: 0.0 }
    }

    #[must_use]
    pub fn distance(self, other: Self) -> f32 {
        (self.x - other.x).hypot(self.y - other.y)
    }

    #[must_use]
    pub fn midpoint(self, other: Self) -> Self {
        Self {
            x: f32::midpoint(self.x, other.x),
            y: f32::midpoint(self.y, other.y),
            z: f32::midpoint(self.z, other.z),
        }
    }

    fn is_valid(self) -> bool {
        [self.x, self.y]
            .iter()
            .all(|v| v.is_finite() && (COORD_MIN..=COORD_MAX).contains(v))
            && self.z.is_finite()
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Handedness {
    Left,
    Right,
    #[default]
    Unknown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Joint {
    Wrist = 0,
    ThumbCmc = 1,
    ThumbMcp = 2,
    ThumbIp = 3,
    ThumbTip = 4,
    IndexMcp = 5,
    IndexPip = 6,
    IndexDip = 7,
    IndexTip = 8,
    MiddleMcp = 9,
    MiddlePip = 10,
    MiddleDip = 11,
    MiddleTip = 12,
    RingMcp = 13,
    RingPip = 14,
    RingDip = 15,
    RingTip = 16,
    PinkyMcp = 17,
    PinkyPip = 18,
    PinkyDip = 19,
    PinkyTip = 20,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Hand {
    points: [Point; LANDMARKS],
    pub handedness: Handedness,
    pub score: f32,
}

impl Hand {
    pub fn new(points: &[Point], handedness: Handedness, score: f32) -> Result<Self, GestureError> {
        let points: [Point; LANDMARKS] =
            points.try_into().map_err(|_| GestureError::LandmarkCount)?;
        if !points.iter().all(|p| p.is_valid()) {
            return Err(GestureError::LandmarkOutOfRange);
        }
        Ok(Self {
            points,
            handedness,
            score: if score.is_finite() {
                score.clamp(0.0, 1.0)
            } else {
                0.0
            },
        })
    }

    #[must_use]
    pub fn at(&self, joint: Joint) -> Point {
        self.points.get(joint as usize).copied().unwrap_or_default()
    }

    #[must_use]
    pub const fn points(&self) -> &[Point; LANDMARKS] {
        &self.points
    }

    #[must_use]
    pub fn palm_size(&self) -> f32 {
        let size = self.at(Joint::Wrist).distance(self.at(Joint::MiddleMcp));
        if size > 1e-4 { size } else { 0.1 }
    }

    #[must_use]
    pub fn palm_center(&self) -> Point {
        let joints = [
            Joint::Wrist,
            Joint::IndexMcp,
            Joint::MiddleMcp,
            Joint::PinkyMcp,
        ];
        let (sx, sy) = joints
            .iter()
            .map(|j| self.at(*j))
            .fold((0.0, 0.0), |(ax, ay), p| (ax + p.x, ay + p.y));
        Point::new(sx / 4.0, sy / 4.0)
    }

    #[must_use]
    pub fn pinch_ratio(&self) -> f32 {
        self.at(Joint::ThumbTip).distance(self.at(Joint::IndexTip)) / self.palm_size()
    }

    #[must_use]
    pub fn mirrored(&self) -> Self {
        let mut points = self.points;
        for p in &mut points {
            p.x = 1.0 - p.x;
        }
        Self {
            points,
            handedness: self.handedness,
            score: self.score,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Default)]
pub struct Frame {
    pub timestamp_ms: u64,
    pub hands: Vec<Hand>,
}

impl Frame {
    pub fn new(timestamp_ms: u64, hands: Vec<Hand>) -> Result<Self, GestureError> {
        if hands.len() > MAX_HANDS {
            return Err(GestureError::TooManyHands);
        }
        Ok(Self {
            timestamp_ms,
            hands,
        })
    }
}

#[cfg(test)]
pub(crate) mod fixtures {
    use super::{Hand, Handedness, LANDMARKS, Point};
    use crate::error::GestureError;

    pub fn hand_with(
        edits: &[(usize, Point)],
        handedness: Handedness,
    ) -> Result<Hand, GestureError> {
        let mut points = vec![Point::new(0.5, 0.5); LANDMARKS];
        for (index, point) in edits {
            if let Some(slot) = points.get_mut(*index) {
                *slot = *point;
            }
        }
        Hand::new(&points, handedness, 0.9)
    }

    pub fn shaped(
        fingers: [bool; 5],
        origin: Point,
        handedness: Handedness,
    ) -> Result<Hand, GestureError> {
        let wrist = Point::new(origin.x, origin.y + 0.2);
        let column = |dx: f32, extended: bool| -> [Point; 4] {
            let base = Point::new(origin.x + dx, origin.y);
            let tip_y = if extended {
                origin.y - 0.15
            } else {
                origin.y + 0.05
            };
            [
                base,
                Point::new(base.x, origin.y - 0.05),
                Point::new(base.x, f32::midpoint(origin.y - 0.05, tip_y)),
                Point::new(base.x, tip_y),
            ]
        };
        let [thumb, index, middle, ring, pinky] = fingers;
        let thumb_tip = if thumb {
            Point::new(origin.x - 0.16, origin.y + 0.02)
        } else {
            Point::new(origin.x + 0.01, origin.y + 0.06)
        };
        let mut points = vec![
            wrist,
            Point::new(origin.x - 0.05, origin.y + 0.15),
            Point::new(origin.x - 0.08, origin.y + 0.1),
            Point::new(origin.x - 0.1, origin.y + 0.06),
            thumb_tip,
        ];
        for (dx, ext) in [(-0.04, index), (0.0, middle), (0.04, ring), (0.08, pinky)] {
            points.extend(column(dx, ext));
        }
        Hand::new(&points, handedness, 0.95)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_wrong_count_and_out_of_range() {
        assert_eq!(
            Hand::new(&[Point::default(); 3], Handedness::Left, 1.0),
            Err(GestureError::LandmarkCount)
        );
        let mut points = vec![Point::new(0.5, 0.5); LANDMARKS];
        if let Some(p) = points.get_mut(3) {
            p.x = f32::NAN;
        }
        assert_eq!(
            Hand::new(&points, Handedness::Left, 1.0),
            Err(GestureError::LandmarkOutOfRange)
        );
    }

    #[test]
    fn mirror_flips_x() -> Result<(), GestureError> {
        let hand = fixtures::hand_with(&[(8, Point::new(0.2, 0.3))], Handedness::Right)?;
        assert!((hand.mirrored().at(Joint::IndexTip).x - 0.8).abs() < 1e-6);
        Ok(())
    }

    #[test]
    fn frame_limits_hand_count() -> Result<(), GestureError> {
        let hands = vec![fixtures::hand_with(&[], Handedness::Left)?; MAX_HANDS + 1];
        assert_eq!(Frame::new(0, hands), Err(GestureError::TooManyHands));
        Ok(())
    }
}
