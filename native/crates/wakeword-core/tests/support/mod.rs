#![allow(
    clippy::cast_sign_loss,
    clippy::many_single_char_names,
    clippy::unreadable_literal,
    clippy::similar_names
)]
#![allow(
    dead_code,
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation
)]

use std::f32::consts::PI;

pub const RATE: f32 = 16_000.0;

pub type Segment = (f32, f32, f32);

pub const KEY: [Segment; 5] = [
    (300.0, 2200.0, 90.0),
    (700.0, 1200.0, 140.0),
    (400.0, 1800.0, 100.0),
    (800.0, 1300.0, 150.0),
    (350.0, 2300.0, 120.0),
];

pub const OTHER_A: [Segment; 4] = [
    (600.0, 1000.0, 160.0),
    (300.0, 800.0, 100.0),
    (700.0, 1800.0, 140.0),
    (350.0, 900.0, 160.0),
];

pub const OTHER_B: [Segment; 4] = [
    (250.0, 2400.0, 120.0),
    (250.0, 2400.0, 100.0),
    (800.0, 1100.0, 200.0),
    (500.0, 1500.0, 150.0),
];

pub const OTHER_C: [Segment; 5] = [
    (500.0, 1500.0, 110.0),
    (700.0, 1200.0, 110.0),
    (300.0, 2200.0, 110.0),
    (400.0, 800.0, 110.0),
    (800.0, 1300.0, 110.0),
];

#[derive(Debug)]
pub struct Rng(u64);

impl Rng {
    pub fn new(seed: u64) -> Self {
        Self(seed | 1)
    }

    pub fn next(&mut self) -> f32 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        ((self.0 >> 40) as f32 / (1u64 << 24) as f32) * 2.0 - 1.0
    }
}

pub fn word(segments: &[Segment], pitch: f32, tempo: f32, seed: u64) -> Vec<f32> {
    let mut rng = Rng::new(seed);
    let mut out = Vec::new();
    let mut phase = 0.0f32;
    let mut prev = (segments[0].0, segments[0].1);
    for &(f1, f2, ms) in segments {
        let n = (ms * tempo * RATE / 1000.0) as usize;
        for i in 0..n {
            let t = i as f32 / n as f32;
            let a = prev.0 + (f1 - prev.0) * t;
            let b = prev.1 + (f2 - prev.1) * t;
            let f0 = pitch * (1.0 + 0.02 * (2.0 * PI * 5.0 * out.len() as f32 / RATE).sin());
            phase += 2.0 * PI * f0 / RATE;
            let mut s = 0.0;
            for h in 1..=24 {
                let fh = f0 * h as f32;
                if fh > 4000.0 {
                    break;
                }
                let amp = (-((fh - a) / 150.0).powi(2)).exp()
                    + 0.7 * (-((fh - b) / 250.0).powi(2)).exp()
                    + 0.02;
                s += amp * (phase * h as f32).sin();
            }
            let env = (t * PI).sin().sqrt().max(0.25);
            out.push(0.12 * env * s + 0.002 * rng.next());
        }
        prev = (f1, f2);
    }
    out
}

pub fn pad(
    mut samples: Vec<f32>,
    before_ms: f32,
    after_ms: f32,
    noise: f32,
    seed: u64,
) -> Vec<f32> {
    let mut rng = Rng::new(seed);
    let head = (before_ms * RATE / 1000.0) as usize;
    let tail = (after_ms * RATE / 1000.0) as usize;
    let mut out = vec![0.0; head];
    out.append(&mut samples);
    out.extend(std::iter::repeat_n(0.0, tail));
    for s in &mut out {
        *s += noise * rng.next();
    }
    out
}

pub fn concat(parts: &[Vec<f32>]) -> Vec<f32> {
    parts.iter().flatten().copied().collect()
}

pub fn to_pcm(samples: &[f32]) -> Vec<i16> {
    samples
        .iter()
        .map(|s| (s.clamp(-1.0, 1.0) * 32767.0) as i16)
        .collect()
}

pub fn noise(seconds: f32, amp: f32, seed: u64) -> Vec<f32> {
    let mut rng = Rng::new(seed);
    (0..(seconds * RATE) as usize)
        .map(|_| amp * rng.next())
        .collect()
}
