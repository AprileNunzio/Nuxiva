use serde_json::{Value, json};

use crate::error::{HoloError, HoloResult};
use crate::{layout, parse};

pub const MIN_PAIRS: usize = 4;
pub const MAX_PAIRS: usize = 40;
pub const GENERATED_PARTS: usize = 400;
const TWIST_DEG: f32 = 34.29;
const RISE: f32 = 3.38;
const GROOVE_DEG: f32 = 154.0;
const PHOSPHATE_R: f32 = 8.9;
const SUGAR_R: f32 = 7.0;
const DEFAULT: &str = "ATGCGTACCGATTGCAGCTA";

fn pair_of(base: char) -> Option<char> {
    match base {
        'A' => Some('T'),
        'T' => Some('A'),
        'G' => Some('C'),
        'C' => Some('G'),
        _ => None,
    }
}

fn color(base: char) -> &'static str {
    match base {
        'A' => "#ef476f",
        'T' => "#ffd166",
        'G' => "#06d6a0",
        _ => "#118ab2",
    }
}

fn key(base: char) -> &'static str {
    match base {
        'A' => "dna_adenine",
        'T' => "dna_thymine",
        'G' => "dna_guanine",
        _ => "dna_cytosine",
    }
}

fn point(radius: f32, angle_deg: f32, y: f32) -> [f32; 3] {
    let a = angle_deg.to_radians();
    [radius * a.cos(), y, radius * a.sin()]
}

fn sub(a: [f32; 3], b: [f32; 3]) -> [f32; 3] {
    [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
}

fn lerp(a: [f32; 3], b: [f32; 3], t: f32) -> [f32; 3] {
    [
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    ]
}

fn rod(name: &str, from: [f32; 3], to: [f32; 3], radius: f32, color: &str, layer: u8) -> Value {
    let d = sub(to, from);
    let length = d.iter().map(|v| v * v).sum::<f32>().sqrt().max(1e-4);
    let z = (-(d[0] / length)).clamp(-1.0, 1.0).asin().to_degrees();
    let x = d[2].atan2(d[1]).to_degrees();
    json!({"name": name, "shape": "cylinder", "radius": radius, "height": length,
           "position": lerp(from, to, 0.5), "rotation": [x, 0.0, z], "color": color,
           "roughness": 0.35, "layer": layer})
}

fn ball(name: &str, at: [f32; 3], radius: f32, color: &str, layer: u8) -> Value {
    json!({"name": name, "shape": "sphere", "radius": radius, "position": at, "color": color,
           "roughness": 0.3, "layer": layer})
}

#[must_use]
pub fn sequence(raw: &str) -> String {
    let clean: String = raw
        .chars()
        .map(|c| c.to_ascii_uppercase())
        .filter(|c| pair_of(*c).is_some())
        .take(MAX_PAIRS)
        .collect();
    let source = if clean.len() >= MIN_PAIRS {
        clean
    } else {
        DEFAULT.to_owned()
    };
    source.chars().take(MAX_PAIRS).collect()
}

#[allow(clippy::cast_precision_loss)]
#[must_use]
pub fn parts(seq: &str) -> Vec<Value> {
    let mut out = Vec::new();
    let mut previous: Option<([f32; 3], [f32; 3])> = None;
    for (index, base) in seq.chars().enumerate() {
        let Some(partner) = pair_of(base) else {
            continue;
        };
        let step = index as f32;
        let y = step * RISE;
        let angle = step * TWIST_DEG;
        let p1 = point(PHOSPHATE_R, angle, y);
        let p2 = point(PHOSPHATE_R, angle + GROOVE_DEG, y);
        let s1 = point(SUGAR_R, angle + 8.0, y);
        let s2 = point(SUGAR_R, angle + GROOVE_DEG - 8.0, y);
        let middle = lerp(s1, s2, 0.5);
        out.push(ball("dna_phosphate", p1, 1.35, "#ff9f1c", 0));
        out.push(ball("dna_phosphate", p2, 1.35, "#ff9f1c", 0));
        out.push(ball("dna_sugar", s1, 1.1, "#c9ada7", 0));
        out.push(ball("dna_sugar", s2, 1.1, "#c9ada7", 0));
        out.push(rod(key(base), s1, middle, 0.75, color(base), 1));
        out.push(rod(key(partner), middle, s2, 0.75, color(partner), 1));
        out.push(ball("dna_hydrogen_bond", middle, 0.45, "#e0fbfc", 1));
        if let Some((q1, q2)) = previous {
            out.push(rod("dna_backbone", q1, p1, 0.55, "#8ecae6", 0));
            out.push(rod("dna_backbone", q2, p2, 0.55, "#8ecae6", 0));
        }
        previous = Some((p1, p2));
    }
    out
}

pub fn generate(raw_sequence: &str) -> HoloResult<String> {
    let seq = sequence(raw_sequence);
    let input = json!({"title": "DNA", "source": "model", "parts": parts(&seq)});
    let scene = layout::arrange(parse::scene_limited(&input, GENERATED_PARTS)?);
    serde_json::to_string(&scene).map_err(|_| HoloError::BadJson)
}
