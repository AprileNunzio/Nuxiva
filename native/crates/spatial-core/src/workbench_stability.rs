use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SceneState {
    Warmup,
    OperatorWorking,
    StableBoard,
}

impl SceneState {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Warmup => "warmup",
            Self::OperatorWorking => "operator_working",
            Self::StableBoard => "stable_board",
        }
    }
}

#[derive(Debug, Clone)]
pub struct StabilityGate {
    previous: Vec<u8>,
    motion_threshold: f64,
    required_stable_frames: u32,
    stable_frames: u32,
    state: SceneState,
}

impl StabilityGate {
    #[must_use]
    pub fn new(motion_threshold: f64, required_stable_frames: u32) -> Self {
        Self {
            previous: Vec::new(),
            motion_threshold: motion_threshold.max(0.0),
            required_stable_frames: required_stable_frames.max(1),
            stable_frames: 0,
            state: SceneState::Warmup,
        }
    }

    pub fn observe(&mut self, grid: &[u8]) -> SceneState {
        if grid.is_empty() || self.previous.len() != grid.len() {
            self.previous = grid.to_vec();
            self.stable_frames = 0;
            self.state = SceneState::Warmup;
            return self.state;
        }
        let motion = mean_abs_difference(&self.previous, grid);
        self.previous.clear();
        self.previous.extend_from_slice(grid);
        if motion > self.motion_threshold {
            self.stable_frames = 0;
            self.state = SceneState::OperatorWorking;
        } else {
            self.stable_frames = self.stable_frames.saturating_add(1);
            if self.stable_frames >= self.required_stable_frames {
                self.state = SceneState::StableBoard;
            }
        }
        self.state
    }

    #[must_use]
    pub const fn state(&self) -> SceneState {
        self.state
    }

    pub fn reset(&mut self) {
        self.previous.clear();
        self.stable_frames = 0;
        self.state = SceneState::Warmup;
    }
}

impl Default for StabilityGate {
    fn default() -> Self {
        Self::new(6.0, 3)
    }
}

fn mean_abs_difference(left: &[u8], right: &[u8]) -> f64 {
    let total: u64 = left
        .iter()
        .zip(right)
        .map(|(a, b)| u64::from(a.abs_diff(*b)))
        .sum();
    let total = f64::from(u32::try_from(total).unwrap_or(u32::MAX));
    let count = f64::from(u32::try_from(left.len()).unwrap_or(u32::MAX));
    total / count.max(1.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn warmup_then_stable_after_required_frames() {
        let mut gate = StabilityGate::new(4.0, 2);
        let frame = vec![100_u8; 64];
        assert_eq!(gate.observe(&frame), SceneState::Warmup);
        assert_eq!(gate.observe(&frame), SceneState::Warmup);
        assert_eq!(gate.observe(&frame), SceneState::StableBoard);
    }

    #[test]
    fn motion_resets_stability() {
        let mut gate = StabilityGate::new(4.0, 1);
        let still = vec![100_u8; 64];
        let moving = vec![180_u8; 64];
        gate.observe(&still);
        assert_eq!(gate.observe(&still), SceneState::StableBoard);
        assert_eq!(gate.observe(&moving), SceneState::OperatorWorking);
    }

    #[test]
    fn size_change_restarts_warmup() {
        let mut gate = StabilityGate::default();
        gate.observe(&[1, 2, 3]);
        assert_eq!(gate.observe(&[1, 2, 3, 4]), SceneState::Warmup);
    }
}
