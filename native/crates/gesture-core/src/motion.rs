use crate::duo::wrap;
use crate::gesture::{Direction, GestureKind, Rotation};
use crate::landmarks::Point;
use crate::pose::Pose;
use crate::profile::MotionTuning;
use std::collections::VecDeque;
use std::f32::consts::PI;

const TRAIL_CAP: usize = 256;
const CIRCLE_SWEEP: f32 = 2.0 * PI * 0.85;
const TAP_DRIFT: f32 = 0.03;

#[derive(Debug, Clone, PartialEq, Default)]
pub struct MotionTracker {
    trail: VecDeque<(u64, Point)>,
    cooldown_until: u64,
    pose: Option<Pose>,
    pose_since: u64,
    pose_frames: u32,
    announced: Option<Pose>,
    held: bool,
    press: Option<(u64, Point)>,
    last_tap: Option<u64>,
}

#[allow(clippy::cast_precision_loss)]
fn seconds(ms: u64) -> f32 {
    ms as f32 / 1000.0
}

fn swipe(trail: &VecDeque<(u64, Point)>, tuning: &MotionTuning) -> Option<Direction> {
    let (t0, a) = *trail.front()?;
    let (t1, b) = *trail.back()?;
    let elapsed = seconds(t1.saturating_sub(t0)).max(1e-3);
    let (dx, dy) = (b.x - a.x, b.y - a.y);
    let distance = dx.hypot(dy);
    if distance < tuning.swipe_distance || distance / elapsed < tuning.swipe_speed {
        return None;
    }
    if dx.abs() >= 2.0 * dy.abs() {
        Some(if dx > 0.0 {
            Direction::Right
        } else {
            Direction::Left
        })
    } else if dy.abs() >= 2.0 * dx.abs() {
        Some(if dy > 0.0 {
            Direction::Down
        } else {
            Direction::Up
        })
    } else {
        None
    }
}

fn circle(trail: &VecDeque<(u64, Point)>, tuning: &MotionTuning) -> Option<Rotation> {
    if trail.len() < 8 {
        return None;
    }
    #[allow(clippy::cast_precision_loss)]
    let count = trail.len() as f32;
    let cx = trail.iter().map(|(_, p)| p.x).sum::<f32>() / count;
    let cy = trail.iter().map(|(_, p)| p.y).sum::<f32>() / count;
    let centre = Point::new(cx, cy);
    let radii: Vec<f32> = trail.iter().map(|(_, p)| p.distance(centre)).collect();
    let mean = radii.iter().sum::<f32>() / count;
    if mean < tuning.circle_min_radius || radii.iter().any(|r| *r < mean * 0.35) {
        return None;
    }
    let angles: Vec<f32> = trail
        .iter()
        .map(|(_, p)| (p.y - cy).atan2(p.x - cx))
        .collect();
    let sweep: f32 = angles
        .windows(2)
        .map(|w| match w {
            [a, b] => wrap(b - a),
            _ => 0.0,
        })
        .sum();
    if sweep >= CIRCLE_SWEEP {
        Some(Rotation::Clockwise)
    } else if sweep <= -CIRCLE_SWEEP {
        Some(Rotation::CounterClockwise)
    } else {
        None
    }
}

impl MotionTracker {
    pub fn reset(&mut self) {
        *self = Self::default();
    }

    fn track_pose(
        &mut self,
        now: u64,
        pose: Pose,
        tuning: &MotionTuning,
        out: &mut Vec<GestureKind>,
    ) {
        if self.pose == Some(pose) {
            self.pose_frames = self.pose_frames.saturating_add(1);
        } else {
            self.pose = Some(pose);
            self.pose_since = now;
            self.pose_frames = 1;
            self.held = false;
        }
        if pose == Pose::Unknown || self.pose_frames < tuning.stable_frames {
            return;
        }
        if self.announced != Some(pose) {
            self.announced = Some(pose);
            out.push(GestureKind::Pose(pose));
        }
        if !self.held && now.saturating_sub(self.pose_since) >= u64::from(tuning.hold_ms) {
            self.held = true;
            out.push(GestureKind::Hold(pose));
        }
    }

    fn track_path(
        &mut self,
        now: u64,
        palm: Point,
        pose: Pose,
        tuning: &MotionTuning,
        out: &mut Vec<GestureKind>,
    ) {
        if matches!(pose, Pose::Pinch | Pose::OkSign) {
            self.trail.clear();
            return;
        }
        self.trail.push_back((now, palm));
        let horizon = u64::from(tuning.circle_window_ms.max(tuning.swipe_window_ms));
        while self.trail.len() > TRAIL_CAP
            || self
                .trail
                .front()
                .is_some_and(|(t, _)| now.saturating_sub(*t) > horizon)
        {
            self.trail.pop_front();
        }
        if now < self.cooldown_until {
            return;
        }
        let window = u64::from(tuning.swipe_window_ms);
        let recent: VecDeque<(u64, Point)> = self
            .trail
            .iter()
            .filter(|(t, _)| now.saturating_sub(*t) <= window)
            .copied()
            .collect();
        let found = circle(&self.trail, tuning)
            .map(GestureKind::Circle)
            .or_else(|| swipe(&recent, tuning).map(GestureKind::Swipe));
        if let Some(kind) = found {
            out.push(kind);
            self.trail.clear();
            self.cooldown_until = now.saturating_add(u64::from(tuning.cooldown_ms));
        }
    }

    pub fn update(
        &mut self,
        now: u64,
        palm: Point,
        pose: Pose,
        tuning: &MotionTuning,
    ) -> Vec<GestureKind> {
        let mut out = Vec::new();
        self.track_pose(now, pose, tuning, &mut out);
        self.track_path(now, palm, pose, tuning, &mut out);
        out
    }

    pub fn pinch_edge(
        &mut self,
        now: u64,
        down: bool,
        at: Point,
        tuning: &MotionTuning,
    ) -> Option<GestureKind> {
        if down {
            self.press = Some((now, at));
            return None;
        }
        let (start, origin) = self.press.take()?;
        if now.saturating_sub(start) > u64::from(tuning.tap_max_ms)
            || origin.distance(at) > TAP_DRIFT
        {
            return None;
        }
        let double = self
            .last_tap
            .is_some_and(|last| now.saturating_sub(last) <= u64::from(tuning.double_tap_ms));
        if double {
            self.last_tap = None;
            Some(GestureKind::DoubleTap)
        } else {
            self.last_tap = Some(now);
            Some(GestureKind::Tap)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run(points: &[(u64, Point)], pose: Pose) -> Vec<GestureKind> {
        let tuning = MotionTuning::default();
        let mut tracker = MotionTracker::default();
        points
            .iter()
            .flat_map(|(t, p)| tracker.update(*t, *p, pose, &tuning))
            .collect()
    }

    #[test]
    fn detects_swipe_right_once() {
        let path: Vec<(u64, Point)> = (0..10_u16)
            .map(|i| {
                (
                    u64::from(i) * 30,
                    Point::new(0.2 + f32::from(i) * 0.05, 0.5),
                )
            })
            .collect();
        let events = run(&path, Pose::OpenPalm);
        assert_eq!(
            events
                .iter()
                .filter(|e| matches!(e, GestureKind::Swipe(_)))
                .collect::<Vec<_>>(),
            vec![&GestureKind::Swipe(Direction::Right)]
        );
    }

    #[test]
    fn slow_drift_is_not_a_swipe() {
        let path: Vec<(u64, Point)> = (0..40_u16)
            .map(|i| {
                (
                    u64::from(i) * 100,
                    Point::new(0.2 + f32::from(i) * 0.005, 0.5),
                )
            })
            .collect();
        assert!(
            !run(&path, Pose::OpenPalm)
                .iter()
                .any(|e| matches!(e, GestureKind::Swipe(_)))
        );
    }

    #[test]
    fn detects_clockwise_circle() {
        let path: Vec<(u64, Point)> = (0..40_u16)
            .map(|i| {
                let a = f32::from(i) / 36.0 * 2.0 * PI;
                (
                    u64::from(i) * 30,
                    Point::new(0.5 + 0.1 * a.cos(), 0.5 + 0.1 * a.sin()),
                )
            })
            .collect();
        assert!(run(&path, Pose::Point).contains(&GestureKind::Circle(Rotation::Clockwise)));
    }

    #[test]
    fn pose_then_hold() {
        let path: Vec<(u64, Point)> = (0..30_u16)
            .map(|i| (u64::from(i) * 40, Point::new(0.5, 0.5)))
            .collect();
        let events = run(&path, Pose::Fist);
        assert_eq!(
            events,
            vec![GestureKind::Pose(Pose::Fist), GestureKind::Hold(Pose::Fist)]
        );
    }

    #[test]
    fn tap_and_double_tap() {
        let tuning = MotionTuning::default();
        let mut tracker = MotionTracker::default();
        let at = Point::new(0.5, 0.5);
        assert_eq!(tracker.pinch_edge(0, true, at, &tuning), None);
        assert_eq!(
            tracker.pinch_edge(100, false, at, &tuning),
            Some(GestureKind::Tap)
        );
        assert_eq!(tracker.pinch_edge(200, true, at, &tuning), None);
        assert_eq!(
            tracker.pinch_edge(300, false, at, &tuning),
            Some(GestureKind::DoubleTap)
        );
        assert_eq!(tracker.pinch_edge(1000, true, at, &tuning), None);
        assert_eq!(tracker.pinch_edge(2000, false, at, &tuning), None);
    }
}
