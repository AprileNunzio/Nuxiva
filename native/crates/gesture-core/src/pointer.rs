use crate::events::{GestureEvent, PointerPhase};
use crate::gesture::Direction;
use crate::landmarks::{Hand, Joint, Point};
use crate::profile::GestureProfile;
use std::collections::VecDeque;

#[derive(Debug, Clone, PartialEq)]
pub struct PointerTracker {
    x: f32,
    y: f32,
    seen: Option<u64>,
    pinch: bool,
    ignore: bool,
    trail: VecDeque<(u64, Point)>,
}

impl Default for PointerTracker {
    fn default() -> Self {
        Self {
            x: 0.5,
            y: 0.5,
            seen: None,
            pinch: false,
            ignore: false,
            trail: VecDeque::new(),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PinchEdge {
    Pressed,
    Released,
}

fn unit(value: f32) -> f32 {
    value.clamp(0.0, 1.0)
}

impl PointerTracker {
    #[must_use]
    pub const fn pinching(&self) -> bool {
        self.pinch
    }

    #[must_use]
    pub const fn position(&self) -> Point {
        Point::new(self.x, self.y)
    }

    #[must_use]
    pub fn to_screen(profile: &GestureProfile, p: Point) -> Point {
        let z = profile.zone;
        Point::new(
            unit((p.x - z.x0) / (z.x1 - z.x0)),
            unit((p.y - z.y0) / (z.y1 - z.y0)),
        )
    }

    fn event(&self, phase: PointerPhase, flick: Option<Direction>) -> GestureEvent {
        GestureEvent::Pointer {
            phase,
            x: self.x,
            y: self.y,
            pinch: self.pinch,
            flick,
        }
    }

    fn flick(&self, profile: &GestureProfile) -> Option<Direction> {
        let (t0, a) = *self.trail.front()?;
        let (t1, b) = *self.trail.back()?;
        if t1 <= t0 {
            return None;
        }
        #[allow(clippy::cast_precision_loss)]
        let vx = (b.x - a.x) / (t1.saturating_sub(t0) as f32 / 1000.0);
        if vx.abs() <= profile.flick_speed {
            return None;
        }
        Some(if vx > 0.0 {
            Direction::Right
        } else {
            Direction::Left
        })
    }

    fn remember(&mut self, now: u64, window: u32) {
        self.trail.push_back((now, self.position()));
        while self
            .trail
            .front()
            .is_some_and(|(t, _)| now.saturating_sub(*t) >= u64::from(window))
        {
            self.trail.pop_front();
        }
    }

    pub fn release(&mut self, profile: &GestureProfile) -> Option<GestureEvent> {
        if !self.pinch {
            return None;
        }
        self.pinch = false;
        let flick = self.flick(profile);
        self.trail.clear();
        Some(self.event(PointerPhase::Up, flick))
    }

    pub fn lock_after_duo(&mut self) {
        self.ignore = true;
    }

    pub fn track(
        &mut self,
        hand: &Hand,
        ratio: f32,
        now: u64,
        duo_active: bool,
        profile: &GestureProfile,
    ) -> (Vec<GestureEvent>, Option<PinchEdge>) {
        let grip = self.pinch || ratio < profile.pinch_on;
        let tip = if grip {
            hand.at(Joint::ThumbTip).midpoint(hand.at(Joint::IndexTip))
        } else {
            hand.at(Joint::IndexTip)
        };
        let target = Self::to_screen(profile, tip);
        let recent = self
            .seen
            .is_some_and(|s| now.saturating_sub(s) < u64::from(profile.follow_window_ms));
        let k = if recent { profile.follow } else { 1.0 };
        self.x += (target.x - self.x) * k;
        self.y += (target.y - self.y) * k;
        self.seen = Some(now);
        if self.ignore && ratio > profile.pinch_off {
            self.ignore = false;
        }
        let locked = duo_active || self.ignore;
        let mut events = Vec::new();
        let mut edge = None;
        if !locked && !self.pinch && ratio < profile.pinch_on {
            self.pinch = true;
            self.trail.clear();
            self.remember(now, profile.flick_window_ms);
            events.push(self.event(PointerPhase::Down, None));
            edge = Some(PinchEdge::Pressed);
        } else if !locked && self.pinch && ratio > profile.pinch_off {
            events.extend(self.release(profile));
            edge = Some(PinchEdge::Released);
        } else if !locked && self.pinch {
            self.remember(now, profile.flick_window_ms);
            events.push(self.event(PointerPhase::Drag, None));
        } else {
            events.push(self.event(PointerPhase::Move, None));
        }
        (events, edge)
    }

    pub fn lost(&mut self, now: u64, profile: &GestureProfile) -> Vec<GestureEvent> {
        let Some(seen) = self.seen else {
            return Vec::new();
        };
        if now.saturating_sub(seen) <= u64::from(profile.lost_ms) {
            return Vec::new();
        }
        let mut events: Vec<GestureEvent> = self.release(profile).into_iter().collect();
        events.push(self.event(PointerPhase::Hidden, None));
        self.seen = None;
        self.ignore = false;
        events
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::error::GestureError;
    use crate::landmarks::Handedness;
    use crate::landmarks::fixtures::hand_with;

    fn hand(pinched: bool, x: f32) -> Result<Hand, GestureError> {
        let gap = if pinched { 0.01 } else { 0.2 };
        hand_with(
            &[
                (0, Point::new(x, 0.7)),
                (9, Point::new(x, 0.5)),
                (4, Point::new(x - gap / 2.0, 0.4)),
                (8, Point::new(x + gap / 2.0, 0.4)),
            ],
            Handedness::Right,
        )
    }

    fn ratio(pinched: bool) -> f32 {
        if pinched { 0.05 } else { 1.0 }
    }

    fn phases(events: &[GestureEvent]) -> Vec<PointerPhase> {
        events
            .iter()
            .filter_map(|e| match e {
                GestureEvent::Pointer { phase, .. } => Some(*phase),
                _ => None,
            })
            .collect()
    }

    #[test]
    fn press_drag_release_and_flick() -> Result<(), GestureError> {
        let profile = GestureProfile::default();
        let mut pointer = PointerTracker::default();
        assert_eq!(
            phases(
                &pointer
                    .track(&hand(false, 0.5)?, ratio(false), 0, false, &profile)
                    .0
            ),
            vec![PointerPhase::Move]
        );
        let (down, edge) = pointer.track(&hand(true, 0.5)?, ratio(true), 30, false, &profile);
        assert_eq!(
            (phases(&down), edge),
            (vec![PointerPhase::Down], Some(PinchEdge::Pressed))
        );
        assert_eq!(
            phases(
                &pointer
                    .track(&hand(true, 0.7)?, ratio(true), 60, false, &profile)
                    .0
            ),
            vec![PointerPhase::Drag]
        );
        let (up, _) = pointer.track(&hand(false, 0.85)?, ratio(false), 90, false, &profile);
        assert!(matches!(
            up.first(),
            Some(GestureEvent::Pointer {
                phase: PointerPhase::Up,
                flick: Some(Direction::Right),
                ..
            })
        ));
        Ok(())
    }

    #[test]
    fn duo_locks_until_pinch_opens() -> Result<(), GestureError> {
        let profile = GestureProfile::default();
        let mut pointer = PointerTracker::default();
        pointer.lock_after_duo();
        assert_eq!(
            phases(
                &pointer
                    .track(&hand(true, 0.5)?, ratio(true), 0, false, &profile)
                    .0
            ),
            vec![PointerPhase::Move]
        );
        let _ = pointer.track(&hand(false, 0.5)?, ratio(false), 30, false, &profile);
        assert_eq!(
            phases(
                &pointer
                    .track(&hand(true, 0.5)?, ratio(true), 60, false, &profile)
                    .0
            ),
            vec![PointerPhase::Down]
        );
        Ok(())
    }

    #[test]
    fn lost_hand_releases_and_hides() -> Result<(), GestureError> {
        let profile = GestureProfile::default();
        let mut pointer = PointerTracker::default();
        let _ = pointer.track(&hand(true, 0.5)?, ratio(true), 0, false, &profile);
        assert!(pointer.lost(500, &profile).is_empty());
        assert_eq!(
            phases(&pointer.lost(800, &profile)),
            vec![PointerPhase::Up, PointerPhase::Hidden]
        );
        Ok(())
    }
}
