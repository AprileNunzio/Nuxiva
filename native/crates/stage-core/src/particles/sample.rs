use serde::{Deserialize, Serialize};
use std::f64::consts::TAU;

use super::codec::{Cloud, MIN_POINTS, ParticleError};

pub const MAX_PARTS: usize = 96;
const QUANT: f64 = 32_767.0;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Shape {
    Sphere,
    Box,
    Cylinder,
    Cone,
    Torus,
    Helix,
    Plane,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Part {
    pub shape: Shape,
    #[serde(default = "unit")]
    pub size: [f64; 3],
    #[serde(default)]
    pub at: [f64; 3],
    #[serde(default)]
    pub rot: [f64; 3],
    #[serde(default = "white")]
    pub color: String,
    #[serde(default = "one")]
    pub weight: f64,
}

const fn unit() -> [f64; 3] {
    [1.0, 1.0, 1.0]
}

fn white() -> String {
    "#9be7ff".to_owned()
}

const fn one() -> f64 {
    1.0
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Spec {
    pub parts: Vec<Part>,
}

#[derive(Debug, Clone)]
struct Rng(u64);

impl Rng {
    fn next_f64(&mut self) -> f64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^= z >> 31;
        #[allow(clippy::cast_precision_loss)]
        let v = (z >> 11) as f64;
        v / 9_007_199_254_740_992.0
    }
}

fn finite_in(v: f64, lo: f64, hi: f64) -> bool {
    v.is_finite() && v >= lo && v <= hi
}

fn parse_color(hex: &str) -> Option<[u8; 3]> {
    let digits = hex.strip_prefix('#')?;
    if digits.len() != 6 || !digits.bytes().all(|b| b.is_ascii_hexdigit()) {
        return None;
    }
    let byte = |range: std::ops::Range<usize>| {
        digits
            .get(range)
            .and_then(|s| u8::from_str_radix(s, 16).ok())
    };
    Some([byte(0..2)?, byte(2..4)?, byte(4..6)?])
}

fn validate(spec: &Spec) -> Result<Vec<[u8; 3]>, ParticleError> {
    if spec.parts.is_empty() || spec.parts.len() > MAX_PARTS {
        return Err(ParticleError::Spec("parts must be between 1 and 96"));
    }
    let mut colors = Vec::with_capacity(spec.parts.len());
    for part in &spec.parts {
        if !part.size.iter().all(|v| finite_in(*v, 0.01, 10.0)) {
            return Err(ParticleError::Spec("size out of range"));
        }
        if !part.at.iter().all(|v| finite_in(*v, -10.0, 10.0)) {
            return Err(ParticleError::Spec("position out of range"));
        }
        if !part.rot.iter().all(|v| finite_in(*v, -360.0, 360.0)) {
            return Err(ParticleError::Spec("rotation out of range"));
        }
        if !finite_in(part.weight, 0.05, 10.0) {
            return Err(ParticleError::Spec("weight out of range"));
        }
        colors.push(parse_color(&part.color).ok_or(ParticleError::Spec("color must be #rrggbb"))?);
    }
    Ok(colors)
}

fn shares(parts: &[Part], count: u32) -> Vec<u32> {
    let mass: Vec<f64> = parts
        .iter()
        .map(|p| {
            let [x, y, z] = p.size;
            p.weight * (x * y + y * z + z * x)
        })
        .collect();
    let total: f64 = mass.iter().sum();
    let exact: Vec<f64> = mass.iter().map(|m| m / total * f64::from(count)).collect();
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    let mut base: Vec<u32> = exact.iter().map(|e| e.floor() as u32).collect();
    let used = base.iter().fold(0_u32, |a, b| a.saturating_add(*b));
    let mut order: Vec<usize> = (0..parts.len()).collect();
    order.sort_by(|a, b| {
        let fa = exact.get(*a).map_or(0.0, |e| e - e.floor());
        let fb = exact.get(*b).map_or(0.0, |e| e - e.floor());
        fb.total_cmp(&fa).then_with(|| a.cmp(b))
    });
    for idx in order.into_iter().take(count.saturating_sub(used) as usize) {
        if let Some(slot) = base.get_mut(idx) {
            *slot = slot.saturating_add(1);
        }
    }
    base
}

fn point(shape: Shape, rng: &mut Rng) -> [f64; 3] {
    let ua = rng.next_f64();
    let ub = rng.next_f64();
    let uc = rng.next_f64();
    match shape {
        Shape::Sphere => {
            let theta = TAU * ua;
            let height = 2.0 * ub - 1.0;
            let radius = (1.0 - height * height).max(0.0).sqrt();
            [radius * theta.cos(), radius * theta.sin(), height]
        }
        Shape::Box => {
            let su = 2.0 * ub - 1.0;
            let sv = 2.0 * uc - 1.0;
            let face = (ua * 6.0).floor();
            if face < 1.0 {
                [1.0, su, sv]
            } else if face < 2.0 {
                [-1.0, su, sv]
            } else if face < 3.0 {
                [su, 1.0, sv]
            } else if face < 4.0 {
                [su, -1.0, sv]
            } else if face < 5.0 {
                [su, sv, 1.0]
            } else {
                [su, sv, -1.0]
            }
        }
        Shape::Cylinder => {
            let theta = TAU * ub;
            if ua < 0.7 {
                [theta.cos(), 2.0 * uc - 1.0, theta.sin()]
            } else {
                let radius = uc.sqrt();
                let cap = if ua < 0.85 { 1.0 } else { -1.0 };
                [radius * theta.cos(), cap, radius * theta.sin()]
            }
        }
        Shape::Cone => {
            let theta = TAU * ub;
            let slope = ua.sqrt();
            [slope * theta.cos(), 1.0 - 2.0 * slope, slope * theta.sin()]
        }
        Shape::Torus => {
            let theta = TAU * ua;
            let phi = TAU * ub;
            let ring = 1.0 + 0.35 * phi.cos();
            [
                ring * theta.cos() / 1.35,
                0.35 * phi.sin() / 1.35,
                ring * theta.sin() / 1.35,
            ]
        }
        Shape::Helix => {
            let turn = 3.0 * TAU * ua;
            let jitter = (ub - 0.5) * 0.08;
            [
                turn.cos() + jitter,
                2.0 * ua - 1.0,
                turn.sin() + (uc - 0.5) * 0.08,
            ]
        }
        Shape::Plane => [2.0 * ua - 1.0, (uc - 0.5) * 0.02, 2.0 * ub - 1.0],
    }
}

fn rotate(p: [f64; 3], deg: [f64; 3]) -> [f64; 3] {
    let [rx, ry, rz] = deg.map(f64::to_radians);
    let [x, y, z] = p;
    let (y, z) = (y * rx.cos() - z * rx.sin(), y * rx.sin() + z * rx.cos());
    let (x, z) = (x * ry.cos() + z * ry.sin(), -x * ry.sin() + z * ry.cos());
    let (x, y) = (x * rz.cos() - y * rz.sin(), x * rz.sin() + y * rz.cos());
    [x, y, z]
}

fn quantize(v: f64) -> i16 {
    let scaled = (v * QUANT).clamp(-QUANT, QUANT);
    #[allow(clippy::cast_possible_truncation)]
    let q = (scaled + 0.5_f64.copysign(scaled)).trunc() as i16;
    q
}

fn shade(channel: u8, factor: f64) -> u8 {
    let v = (f64::from(channel) * factor).clamp(0.0, 255.0);
    #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    let out = (v + 0.5).floor().min(255.0) as u8;
    out
}

pub fn sample(spec: &Spec, count: u32, seed: u64) -> Result<Cloud, ParticleError> {
    if !(MIN_POINTS..=super::codec::MAX_POINTS).contains(&count) {
        return Err(ParticleError::Spec("count out of range"));
    }
    let colors = validate(spec)?;
    let mut rng = Rng(seed);
    let mut raw: Vec<[f64; 3]> = Vec::with_capacity(count as usize);
    let mut tint: Vec<[u8; 3]> = Vec::with_capacity(count as usize);
    for ((part, color), n) in spec
        .parts
        .iter()
        .zip(&colors)
        .zip(shares(&spec.parts, count))
    {
        for _ in 0..n {
            let [x, y, z] = point(part.shape, &mut rng);
            let [sx, sy, sz] = part.size;
            let [px, py, pz] = rotate([x * sx, y * sy, z * sz], part.rot);
            let [ax, ay, az] = part.at;
            raw.push([px + ax, py + ay, pz + az]);
            let factor = 0.85 + 0.3 * rng.next_f64();
            tint.push(color.map(|ch| shade(ch, factor)));
        }
    }
    let reach = raw
        .iter()
        .flat_map(|p| p.iter().map(|v| v.abs()))
        .fold(0.0_f64, f64::max);
    let scale = if reach > 0.0 { 1.0 / reach } else { 1.0 };
    Ok(Cloud {
        positions: raw.iter().map(|p| p.map(|v| quantize(v * scale))).collect(),
        colors: tint,
    })
}
