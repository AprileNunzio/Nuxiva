use serde::{Deserialize, Serialize};

use crate::error::GaitError;

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct GaitObservation {
    pub timestamp_ms: u64,
    pub x: f32,
    pub y: f32,
    pub width: f32,
    pub height: f32,
}

impl GaitObservation {
    #[must_use]
    pub const fn new(timestamp_ms: u64, x: f32, y: f32, width: f32, height: f32) -> Self {
        Self {
            timestamp_ms,
            x,
            y,
            width,
            height,
        }
    }

    pub fn validate(&self) -> Result<(), GaitError> {
        if !self.x.is_finite()
            || !self.y.is_finite()
            || !self.width.is_finite()
            || !self.height.is_finite()
            || self.width <= 0.0
            || self.height <= 0.0
        {
            return Err(GaitError::InvalidBoundingBox);
        }
        Ok(())
    }

    #[must_use]
    pub fn center_x(&self) -> f32 {
        self.x + self.width * 0.5
    }

    #[must_use]
    pub fn center_y(&self) -> f32 {
        self.y + self.height * 0.5
    }

    #[must_use]
    pub fn aspect_ratio(&self) -> f32 {
        if self.height > 0.0 {
            self.width / self.height
        } else {
            0.0
        }
    }
}
