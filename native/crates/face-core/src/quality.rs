#![allow(clippy::cast_precision_loss)]

use crate::image::{Gray, ramp};

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Landmarks {
    pub right_eye: (f32, f32),
    pub left_eye: (f32, f32),
    pub nose: (f32, f32),
    pub mouth_right: (f32, f32),
    pub mouth_left: (f32, f32),
}

impl Landmarks {
    #[must_use]
    pub fn from_slice(v: &[f32]) -> Option<Self> {
        let p = |i: usize| -> Option<(f32, f32)> {
            let x = *v.get(i.checked_mul(2)?)?;
            let y = *v.get(i.checked_mul(2)?.checked_add(1)?)?;
            (x.is_finite() && y.is_finite()).then_some((x, y))
        };
        Some(Self {
            right_eye: p(0)?,
            left_eye: p(1)?,
            nose: p(2)?,
            mouth_right: p(3)?,
            mouth_left: p(4)?,
        })
    }

    #[must_use]
    pub fn eye_span(&self) -> f32 {
        let dx = self.left_eye.0 - self.right_eye.0;
        let dy = self.left_eye.1 - self.right_eye.1;
        dx.hypot(dy).max(1.0)
    }

    #[must_use]
    pub fn pose(&self) -> Pose {
        let span = (self.left_eye.0 - self.right_eye.0).abs().max(1.0);
        let mid_x = f32::midpoint(self.right_eye.0, self.left_eye.0);
        let mid_y = f32::midpoint(self.right_eye.1, self.left_eye.1);
        let yaw_ratio = (self.nose.0 - mid_x) / span;
        let pitch_ratio = (self.nose.1 - mid_y) / span;
        let roll = (self.left_eye.1 - self.right_eye.1)
            .atan2(self.left_eye.0 - self.right_eye.0)
            .to_degrees();
        Pose {
            yaw_ratio,
            pitch_ratio,
            yaw_deg: (yaw_ratio * 2.0).atan().to_degrees(),
            pitch_deg: ((pitch_ratio - 0.72) * 2.0).atan().to_degrees(),
            roll_deg: roll,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Pose {
    pub yaw_ratio: f32,
    pub pitch_ratio: f32,
    pub yaw_deg: f32,
    pub pitch_deg: f32,
    pub roll_deg: f32,
}

impl Pose {
    #[must_use]
    pub fn kind(&self) -> &'static str {
        let (yaw, pitch) = (self.yaw_ratio, self.pitch_ratio);
        if yaw > 0.55 {
            "left"
        } else if yaw < -0.55 {
            "right"
        } else if yaw > 0.22 {
            "three_left"
        } else if yaw < -0.22 {
            "three_right"
        } else if pitch < 0.45 {
            "up"
        } else if pitch > 1.0 {
            "down"
        } else {
            "front"
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Light {
    pub mean: f32,
    pub std: f32,
    pub dark_pct: f32,
    pub bright_pct: f32,
}

#[must_use]
pub fn light(gray: &Gray<'_>) -> Light {
    let n = gray.data.len().max(1) as f32;
    let mean = gray.data.iter().map(|v| f32::from(*v)).sum::<f32>() / n;
    let var = gray
        .data
        .iter()
        .map(|v| (f32::from(*v) - mean) * (f32::from(*v) - mean))
        .sum::<f32>()
        / n;
    #[allow(clippy::cast_precision_loss)]
    let dark = gray.data.iter().filter(|v| **v < 16).count() as f32 / n;
    #[allow(clippy::cast_precision_loss)]
    let bright = gray.data.iter().filter(|v| **v > 245).count() as f32 / n;
    Light {
        mean,
        std: var.sqrt(),
        dark_pct: dark * 100.0,
        bright_pct: bright * 100.0,
    }
}

#[must_use]
pub fn frame_issues(l: &Light) -> Vec<&'static str> {
    let mut out = Vec::new();
    if l.mean < 10.0 && l.std < 6.0 {
        out.push("black");
    } else if l.mean < 45.0 {
        out.push("dark");
    }
    if l.std < 10.0 && l.mean >= 10.0 {
        out.push("flat");
    }
    if l.bright_pct > 25.0 {
        out.push("overexposed");
    }
    out
}

#[must_use]
pub fn sharpness(gray: &Gray<'_>) -> f32 {
    let (w, h) = (gray.width, gray.height);
    let mut values = Vec::with_capacity(w.saturating_mul(h));
    for y in 1..h.saturating_sub(1) {
        for x in 1..w.saturating_sub(1) {
            let c = gray.at(x, y);
            let lap = gray.at(x.saturating_sub(1), y)
                + gray.at(x.saturating_add(1), y)
                + gray.at(x, y.saturating_sub(1))
                + gray.at(x, y.saturating_add(1))
                - 4.0 * c;
            values.push(lap);
        }
    }
    let n = values.len().max(1) as f32;
    let mean = values.iter().sum::<f32>() / n;
    values.iter().map(|v| (v - mean) * (v - mean)).sum::<f32>() / n
}

#[derive(Debug, Clone, PartialEq)]
pub struct Quality {
    pub score: f32,
    pub sharpness: f32,
    pub brightness: f32,
    pub contrast: f32,
    pub face_px: f32,
    pub face_ratio: f32,
    pub eye_px: f32,
    pub pose: Pose,
    pub kind: &'static str,
    pub issues: Vec<&'static str>,
}

#[must_use]
pub fn assess(crop: &Gray<'_>, marks: &Landmarks, face_w: f32, frame_w: f32) -> Quality {
    let l = light(crop);
    let sharp = sharpness(crop);
    let pose = marks.pose();
    let eye_px = marks.eye_span();
    let mut issues = Vec::new();
    let s_sharp = ramp(sharp, 12.0, 110.0);
    let s_light = ramp(l.mean, 35.0, 85.0) * (1.0 - ramp(l.mean, 200.0, 240.0));
    let s_contrast = ramp(l.std, 14.0, 42.0);
    let s_size = ramp(face_w, 56.0, 150.0);
    let s_roll = 1.0 - ramp(pose.roll_deg.abs(), 12.0, 30.0);
    if s_sharp < 0.35 {
        issues.push("blurry");
    }
    if l.mean < 45.0 {
        issues.push("dark");
    }
    if l.mean > 215.0 || l.bright_pct > 20.0 {
        issues.push("overexposed");
    }
    if s_contrast < 0.3 {
        issues.push("low_contrast");
    }
    if s_size < 0.3 {
        issues.push("small");
    }
    if s_roll < 0.5 {
        issues.push("tilted");
    }
    let score =
        100.0 * (0.32 * s_sharp + 0.22 * s_light + 0.16 * s_contrast + 0.2 * s_size + 0.1 * s_roll);
    Quality {
        score,
        sharpness: sharp,
        brightness: l.mean,
        contrast: l.std,
        face_px: face_w,
        face_ratio: if frame_w > 0.0 { face_w / frame_w } else { 0.0 },
        eye_px,
        kind: pose.kind(),
        pose,
        issues,
    }
}
