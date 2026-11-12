use std::collections::VecDeque;

use crate::image::ramp;
use crate::quality::Landmarks;

pub const HISTORY: usize = 24;
pub const MIN_TURN: f32 = 0.06;
pub const FLAT: f32 = 0.03;
pub const DEPTH: f32 = 0.075;
pub const FLAT_PAIRS: usize = 4;
pub const WINDOW_S: f64 = 6.0;

type Point = (f32, f32);

fn solve(mut m: [[f64; 9]; 8]) -> Option<[f64; 8]> {
    for col in 0..8 {
        let pivot = (col..8).max_by(|a, b| {
            let va = m.get(*a).and_then(|r| r.get(col)).map_or(0.0, |v| v.abs());
            let vb = m.get(*b).and_then(|r| r.get(col)).map_or(0.0, |v| v.abs());
            va.total_cmp(&vb)
        })?;
        m.swap(col, pivot);
        let row = *m.get(col)?;
        let p = *row.get(col)?;
        if p.abs() < 1e-12 {
            return None;
        }
        for (r, other) in m.iter_mut().enumerate() {
            if r == col {
                continue;
            }
            let f = other.get(col).copied().unwrap_or(0.0) / p;
            for (o, v) in other.iter_mut().zip(row.iter()) {
                *o -= f * v;
            }
        }
    }
    let mut out = [0.0_f64; 8];
    for (i, slot) in out.iter_mut().enumerate() {
        let row = m.get(i)?;
        *slot = row.get(8)? / row.get(i)?;
    }
    Some(out)
}

fn frame_of(l: &Landmarks) -> (Point, f32) {
    let cx = (l.right_eye.0 + l.left_eye.0 + l.mouth_right.0 + l.mouth_left.0) / 4.0;
    let cy = (l.right_eye.1 + l.left_eye.1 + l.mouth_right.1 + l.mouth_left.1) / 4.0;
    ((cx, cy), l.eye_span())
}

fn norm(p: Point, origin: Point, scale: f32) -> (f64, f64) {
    (
        f64::from((p.0 - origin.0) / scale),
        f64::from((p.1 - origin.1) / scale),
    )
}

#[must_use]
#[allow(clippy::many_single_char_names)]
pub fn planar_residual(a: &Landmarks, b: &Landmarks) -> Option<f32> {
    let (oa, sa) = frame_of(a);
    let (ob, sb) = frame_of(b);
    let src = [a.right_eye, a.left_eye, a.mouth_right, a.mouth_left].map(|p| norm(p, oa, sa));
    let dst = [b.right_eye, b.left_eye, b.mouth_right, b.mouth_left].map(|p| norm(p, ob, sb));
    let mut m = [[0.0_f64; 9]; 8];
    for (i, ((x, y), (u, v))) in src.iter().zip(dst.iter()).enumerate() {
        let r = i.checked_mul(2)?;
        *m.get_mut(r)? = [*x, *y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y, *u];
        *m.get_mut(r.checked_add(1)?)? = [0.0, 0.0, 0.0, *x, *y, 1.0, -v * x, -v * y, *v];
    }
    let h = solve(m)?;
    let (nx, ny) = norm(a.nose, oa, sa);
    let w = h[6] * nx + h[7] * ny + 1.0;
    if w.abs() < 1e-9 {
        return None;
    }
    let px = (h[0] * nx + h[1] * ny + h[2]) / w;
    let py = (h[3] * nx + h[4] * ny + h[5]) / w;
    let (bx, by) = norm(b.nose, ob, sb);
    #[allow(clippy::cast_possible_truncation)]
    let residual = (px - bx).hypot(py - by) as f32;
    residual.is_finite().then_some(residual)
}

fn shape_of(l: &Landmarks) -> f32 {
    let eye_y = f32::midpoint(l.right_eye.1, l.left_eye.1);
    let mouth_y = f32::midpoint(l.mouth_right.1, l.mouth_left.1);
    let mouth_w = (l.mouth_left.0 - l.mouth_right.0).abs();
    ((l.eye_span() + mouth_w) / (mouth_y - eye_y).abs().max(1.0)).max(1e-3)
}

#[derive(Debug, Clone, PartialEq)]
pub struct Aliveness {
    pub state: &'static str,
    pub score: Option<f32>,
    pub depth: f32,
    pub turn: f32,
    pub pairs: usize,
}

#[derive(Debug, Clone, Default)]
pub struct LivenessTracker {
    history: VecDeque<(f64, Landmarks)>,
    best_depth: f32,
    flat_pairs: usize,
    max_turn: f32,
    evidence: Option<f32>,
}

impl LivenessTracker {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn update(&mut self, marks: Landmarks, now: f64, minimum: f32) -> Aliveness {
        let yaw = marks.pose().yaw_ratio;
        let shape = shape_of(&marks);
        while self
            .history
            .front()
            .is_some_and(|(t, _)| now - t > WINDOW_S)
        {
            self.history.pop_front();
        }
        let mut depth_now: Option<f32> = None;
        for (_, old) in &self.history {
            let turn = (old.pose().yaw_ratio - yaw)
                .abs()
                .max((shape_of(old) / shape).ln().abs());
            self.max_turn = self.max_turn.max(turn);
            if turn < MIN_TURN {
                continue;
            }
            if let Some(r) = planar_residual(old, &marks) {
                depth_now = Some(depth_now.map_or(r, |d: f32| d.max(r)));
            }
        }
        if let Some(d) = depth_now {
            self.best_depth = self.best_depth.max(d);
            if d < FLAT {
                self.flat_pairs = self.flat_pairs.saturating_add(1);
            }
            let s = ramp(d, FLAT, DEPTH);
            self.evidence = Some(self.evidence.map_or(s, |e| e + (s - e) * 0.35).max(s * 0.9));
        }
        self.history.push_back((now, marks));
        while self.history.len() > HISTORY {
            self.history.pop_front();
        }
        let state = match self.evidence {
            Some(e) if e >= minimum => "live",
            Some(_) if self.flat_pairs >= FLAT_PAIRS && self.best_depth < DEPTH * 0.6 => "spoof",
            _ => "unknown",
        };
        Aliveness {
            state,
            score: self.evidence,
            depth: self.best_depth,
            turn: self.max_turn,
            pairs: self.flat_pairs,
        }
    }
}
