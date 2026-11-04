use crate::landmarks::{Hand, Joint, Point};
use crate::profile::DuoTuning;
use std::f32::consts::PI;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct DuoPose {
    pub mid: Point,
    pub span: f32,
    pub angle: f32,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct DuoDelta {
    pub scale: f32,
    pub rotate: f32,
    pub pan: Point,
}

impl DuoDelta {
    pub const IDLE: Self = Self {
        scale: 1.0,
        rotate: 0.0,
        pan: Point::new(0.0, 0.0),
    };
}

#[must_use]
pub fn wrap(angle: f32) -> f32 {
    angle.sin().atan2(angle.cos())
}

fn dead(value: f32, zone: f32) -> f32 {
    if value.abs() < zone {
        0.0
    } else {
        value - value.signum() * zone
    }
}

fn grip(hand: &Hand) -> Point {
    hand.at(Joint::ThumbTip).midpoint(hand.at(Joint::IndexTip))
}

#[must_use]
pub fn pair(first: &Hand, second: &Hand) -> DuoPose {
    let (a, b) = (grip(first), grip(second));
    let (left, right) = if a.x <= b.x { (a, b) } else { (b, a) };
    DuoPose {
        mid: a.midpoint(b),
        span: a.distance(b),
        angle: (right.y - left.y).atan2(right.x - left.x),
    }
}

#[must_use]
pub fn blend(previous: Option<DuoPose>, current: DuoPose, smooth: f32) -> DuoPose {
    let Some(prev) = previous else { return current };
    DuoPose {
        mid: Point::new(
            prev.mid.x + (current.mid.x - prev.mid.x) * smooth,
            prev.mid.y + (current.mid.y - prev.mid.y) * smooth,
        ),
        span: prev.span + (current.span - prev.span) * smooth,
        angle: prev.angle + wrap(current.angle - prev.angle) * smooth,
    }
}

#[must_use]
pub fn delta(previous: Option<DuoPose>, current: DuoPose, tuning: &DuoTuning) -> DuoDelta {
    let Some(prev) = previous else {
        return DuoDelta::IDLE;
    };
    if prev.span <= 0.0 || current.span <= 0.0 {
        return DuoDelta::IDLE;
    }
    let limit = tuning.max_scale.ln();
    let ratio = (current.span / prev.span).ln();
    DuoDelta {
        scale: dead(ratio, tuning.dead_scale).clamp(-limit, limit).exp(),
        rotate: dead(wrap(current.angle - prev.angle), tuning.dead_rotate)
            .clamp(-tuning.max_rotate, tuning.max_rotate),
        pan: Point::new(
            dead(current.mid.x - prev.mid.x, tuning.dead_pan),
            dead(current.mid.y - prev.mid.y, tuning.dead_pan),
        ),
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Default)]
pub struct DuoAccumulator {
    scale: f32,
    rotate: f32,
}

impl DuoAccumulator {
    pub fn start(&mut self) {
        *self = Self {
            scale: 1.0,
            rotate: 0.0,
        };
    }

    pub fn push(
        &mut self,
        step: DuoDelta,
        tuning: &DuoTuning,
    ) -> Option<crate::gesture::DuoMotion> {
        use crate::gesture::DuoMotion;
        self.scale *= step.scale;
        self.rotate += step.rotate;
        let fired = if self.scale >= tuning.spread_trigger {
            Some(DuoMotion::Spread)
        } else if self.scale <= 1.0 / tuning.spread_trigger {
            Some(DuoMotion::Squeeze)
        } else if self.rotate >= tuning.rotate_trigger {
            Some(DuoMotion::RotateClockwise)
        } else if self.rotate <= -tuning.rotate_trigger {
            Some(DuoMotion::RotateCounterClockwise)
        } else {
            None
        };
        if fired.is_some() {
            self.start();
        }
        fired
    }
}

#[must_use]
pub const fn full_turn() -> f32 {
    2.0 * PI
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::error::GestureError;
    use crate::landmarks::Handedness;
    use crate::landmarks::fixtures::hand_with;

    fn grip_hand(x: f32, y: f32) -> Result<Hand, GestureError> {
        hand_with(
            &[(4, Point::new(x - 0.01, y)), (8, Point::new(x + 0.01, y))],
            Handedness::Unknown,
        )
    }

    fn pose(ax: f32, ay: f32, bx: f32, by: f32) -> Result<DuoPose, GestureError> {
        Ok(pair(&grip_hand(ax, ay)?, &grip_hand(bx, by)?))
    }

    fn near(a: f32, b: f32, eps: f32) -> bool {
        (a - b).abs() < eps
    }

    #[test]
    fn matches_display_gesture_math() -> Result<(), GestureError> {
        let t = DuoTuning::default();
        let rest = pose(0.3, 0.5, 0.7, 0.5)?;
        assert!(
            near(rest.span, 0.4, 1e-6)
                && near(rest.angle, 0.0, 1e-6)
                && near(rest.mid.x, 0.5, 1e-6)
        );
        let spread = delta(Some(rest), pose(0.2, 0.5, 0.8, 0.5)?, &t);
        assert!(spread.scale > 1.2 && spread.scale <= 1.35 + 1e-5);
        assert!(spread.rotate.abs() < f32::EPSILON);
        assert!(delta(Some(rest), pose(0.4, 0.5, 0.6, 0.5)?, &t).scale < 0.8);
        let turned = delta(Some(rest), pose(0.3, 0.4, 0.7, 0.6)?, &t);
        assert!(turned.rotate > 0.3 && near(turned.scale, 1.0, 0.12));
        assert!(delta(Some(rest), pose(0.3, 0.6, 0.7, 0.4)?, &t).rotate < -0.3);
        let moved = delta(Some(rest), pose(0.4, 0.6, 0.8, 0.6)?, &t);
        assert!(moved.pan.x > 0.05 && moved.pan.y > 0.05 && near(moved.scale, 1.0, 1e-6));
        assert_eq!(delta(Some(rest), rest, &t), DuoDelta::IDLE);
        assert_eq!(
            delta(Some(rest), pose(0.3004, 0.5003, 0.7003, 0.5004)?, &t),
            DuoDelta::IDLE
        );
        assert_eq!(delta(None, rest, &t), DuoDelta::IDLE);
        Ok(())
    }

    #[test]
    fn wraps_and_blends() -> Result<(), GestureError> {
        assert!(near(wrap(full_turn() + 0.1), 0.1, 1e-5));
        let rest = pose(0.3, 0.5, 0.7, 0.5)?;
        let across = delta(
            Some(DuoPose {
                angle: PI - 0.05,
                ..rest
            }),
            DuoPose {
                angle: -PI + 0.05,
                ..rest
            },
            &DuoTuning::default(),
        );
        assert!(across.rotate.abs() < 0.1);
        let target = pose(0.2, 0.5, 0.8, 0.5)?;
        let mut state = None;
        for _ in 0..20 {
            state = Some(blend(state, target, 0.55));
        }
        assert!(state.is_some_and(|s| near(s.span, 0.6, 1e-3)));
        Ok(())
    }

    #[test]
    fn accumulator_fires_discrete_motions() {
        let tuning = DuoTuning::default();
        let mut acc = DuoAccumulator::default();
        acc.start();
        let step = DuoDelta {
            scale: 1.1,
            rotate: 0.0,
            pan: Point::default(),
        };
        let fired: Vec<_> = (0..4).filter_map(|_| acc.push(step, &tuning)).collect();
        assert_eq!(fired, vec![crate::gesture::DuoMotion::Spread]);
    }
}
