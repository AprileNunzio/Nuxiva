use crate::landmarks::{Hand, LANDMARKS, Point};
use std::f32::consts::PI;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct OneEuroConfig {
    pub min_cutoff: f32,
    pub beta: f32,
    pub derivative_cutoff: f32,
}

impl Default for OneEuroConfig {
    fn default() -> Self {
        Self {
            min_cutoff: 1.2,
            beta: 0.02,
            derivative_cutoff: 1.0,
        }
    }
}

fn alpha(cutoff: f32, dt: f32) -> f32 {
    let tau = 1.0 / (2.0 * PI * cutoff.max(1e-3));
    1.0 / (1.0 + tau / dt)
}

#[derive(Debug, Clone, Copy, PartialEq, Default)]
struct Axis {
    value: Option<f32>,
    derivative: f32,
}

impl Axis {
    fn filter(&mut self, raw: f32, dt: f32, config: OneEuroConfig) -> f32 {
        let Some(previous) = self.value else {
            self.value = Some(raw);
            return raw;
        };
        let slope = (raw - previous) / dt;
        let da = alpha(config.derivative_cutoff, dt);
        self.derivative += da * (slope - self.derivative);
        let cutoff = config.min_cutoff + config.beta * self.derivative.abs();
        let next = previous + alpha(cutoff, dt) * (raw - previous);
        self.value = Some(next);
        next
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct HandSmoother {
    axes: Vec<(Axis, Axis)>,
    last_ms: Option<u64>,
}

impl Default for HandSmoother {
    fn default() -> Self {
        Self {
            axes: vec![(Axis::default(), Axis::default()); LANDMARKS],
            last_ms: None,
        }
    }
}

impl HandSmoother {
    pub fn reset(&mut self) {
        *self = Self::default();
    }

    #[must_use]
    pub fn smooth(&mut self, hand: &Hand, timestamp_ms: u64, config: OneEuroConfig) -> Hand {
        let gap = self.last_ms.map(|last| timestamp_ms.saturating_sub(last));
        if gap.is_some_and(|g| g > 1_000) {
            self.reset();
        }
        self.last_ms = Some(timestamp_ms);
        #[allow(clippy::cast_precision_loss)]
        let dt = (gap.unwrap_or(16).max(1) as f32) / 1000.0;
        let points: Vec<Point> = hand
            .points()
            .iter()
            .zip(self.axes.iter_mut())
            .map(|(p, (ax, ay))| Point {
                x: ax.filter(p.x, dt, config),
                y: ay.filter(p.y, dt, config),
                z: p.z,
            })
            .collect();
        Hand::new(&points, hand.handedness, hand.score).unwrap_or_else(|_| hand.clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::error::GestureError;
    use crate::landmarks::Handedness;
    use crate::landmarks::fixtures::hand_with;

    #[test]
    fn damps_jitter_and_follows_moves() -> Result<(), GestureError> {
        let mut smoother = HandSmoother::default();
        let config = OneEuroConfig::default();
        let _ = smoother.smooth(
            &hand_with(&[(8, Point::new(0.5, 0.5))], Handedness::Right)?,
            0,
            config,
        );
        let jitter = smoother.smooth(
            &hand_with(&[(8, Point::new(0.51, 0.5))], Handedness::Right)?,
            16,
            config,
        );
        let moved = jitter.points().get(8).map_or(0.0, |p| p.x);
        assert!(moved > 0.5 && moved < 0.51);
        Ok(())
    }

    #[test]
    fn long_gap_resets_state() -> Result<(), GestureError> {
        let mut smoother = HandSmoother::default();
        let config = OneEuroConfig::default();
        let _ = smoother.smooth(&hand_with(&[], Handedness::Right)?, 0, config);
        let far = smoother.smooth(
            &hand_with(&[(8, Point::new(0.9, 0.9))], Handedness::Right)?,
            5_000,
            config,
        );
        assert!(
            far.points()
                .get(8)
                .is_some_and(|p| (p.x - 0.9).abs() < 1e-6)
        );
        Ok(())
    }
}
