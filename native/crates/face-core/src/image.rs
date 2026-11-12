#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ImageError {
    Shape,
    TooLarge,
}

impl ImageError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Shape => "face.image.shape",
            Self::TooLarge => "face.image.too_large",
        }
    }
}

pub const MAX_SIDE: usize = 4096;

#[derive(Debug, Clone, Copy)]
pub struct Gray<'a> {
    pub data: &'a [u8],
    pub width: usize,
    pub height: usize,
}

impl<'a> Gray<'a> {
    pub fn new(data: &'a [u8], width: usize, height: usize) -> Result<Self, ImageError> {
        if width < 8 || height < 8 {
            return Err(ImageError::Shape);
        }
        if width > MAX_SIDE || height > MAX_SIDE {
            return Err(ImageError::TooLarge);
        }
        if width.checked_mul(height) != Some(data.len()) {
            return Err(ImageError::Shape);
        }
        Ok(Self {
            data,
            width,
            height,
        })
    }

    #[must_use]
    pub fn at(&self, x: usize, y: usize) -> f32 {
        let i = y.saturating_mul(self.width).saturating_add(x);
        f32::from(self.data.get(i).copied().unwrap_or(0))
    }

    #[must_use]
    pub fn resample(&self, side: usize) -> Vec<f32> {
        let mut out = Vec::with_capacity(side.saturating_mul(side));
        #[allow(clippy::cast_precision_loss)]
        let (sx, sy) = (
            self.width as f32 / side as f32,
            self.height as f32 / side as f32,
        );
        let max_x = self.width.saturating_sub(1);
        let max_y = self.height.saturating_sub(1);
        for y in 0..side {
            for x in 0..side {
                #[allow(clippy::cast_precision_loss)]
                let fx = ((x as f32 + 0.5) * sx - 0.5).max(0.0);
                #[allow(clippy::cast_precision_loss)]
                let fy = ((y as f32 + 0.5) * sy - 0.5).max(0.0);
                #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
                let (x0, y0) = (fx.floor() as usize, fy.floor() as usize);
                let (x0, y0) = (x0.min(max_x), y0.min(max_y));
                let (x1, y1) = (
                    x0.saturating_add(1).min(max_x),
                    y0.saturating_add(1).min(max_y),
                );
                #[allow(clippy::cast_precision_loss)]
                let (ax, ay) = (fx - x0 as f32, fy - y0 as f32);
                let top = self.at(x0, y0) * (1.0 - ax) + self.at(x1, y0) * ax;
                let bottom = self.at(x0, y1) * (1.0 - ax) + self.at(x1, y1) * ax;
                out.push(top * (1.0 - ay) + bottom * ay);
            }
        }
        out
    }
}

#[must_use]
pub fn ramp(value: f32, low: f32, high: f32) -> f32 {
    if high <= low {
        return 1.0;
    }
    ((value - low) / (high - low)).clamp(0.0, 1.0)
}
