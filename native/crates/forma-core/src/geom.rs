use serde::Serialize;

use crate::build::{Builder, Prim, V, add, norm, scale, sub};
use crate::plan::{FormaError, MAX_PARTS, Plan, Shape};

const REACH: f64 = 3.0;

#[derive(Debug, Clone, Serialize)]
pub struct Part {
    pub shape: Shape,
    pub size: V,
    pub at: V,
    pub rot: V,
    pub color: String,
    pub weight: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct Label {
    pub name: String,
    pub at: V,
}

#[must_use]
pub fn palette(theme: &str) -> [&'static str; 6] {
    match theme {
        "bioluminescent" => [
            "#4ce6ff", "#7952ec", "#a87bff", "#ff6be5", "#5ef2ff", "#c49bff",
        ],
        "celestial" => [
            "#ffd166", "#5ce1e6", "#480ca8", "#72efdd", "#9b7bff", "#ff9f1c",
        ],
        "botanical" => [
            "#38b000", "#70e000", "#a7c957", "#ff70a6", "#ffb703", "#007200",
        ],
        "fauna" => [
            "#ee9b00", "#ca6702", "#bb3e03", "#0077b6", "#90e0ef", "#f1faee",
        ],
        "mechanical" => [
            "#64dfdf", "#48bfe3", "#5390d9", "#ff9f1c", "#80ffdb", "#7400b8",
        ],
        "microscopic" => [
            "#ff006e", "#00f5d4", "#8338ec", "#fee440", "#3a86ff", "#ffbe0b",
        ],
        "geological" => [
            "#2ec4b6", "#e71d36", "#ff9f1c", "#7209b7", "#e0aaff", "#c77dff",
        ],
        _ => [
            "#5ef2ff", "#9b7bff", "#66ffe3", "#ff7be5", "#7aa2ff", "#ffd166",
        ],
    }
}

fn reach(prims: &[Prim]) -> f64 {
    prims
        .iter()
        .map(|p| match p {
            Prim::Seg { a, b, r0, r1, .. } => {
                let extent = |q: &V| q.iter().map(|v| v.abs()).fold(0.0_f64, f64::max);
                extent(a).max(extent(b)) + r0.max(*r1)
            }
            Prim::Blob { at, size, .. } => {
                at.iter().map(|v| v.abs()).fold(0.0_f64, f64::max)
                    + size.iter().copied().fold(0.0_f64, f64::max)
            }
            Prim::Mark { .. } => 0.0,
        })
        .fold(0.0_f64, f64::max)
}

fn wrap(deg: f64) -> f64 {
    let m = deg.rem_euclid(360.0);
    if m > 180.0 { m - 360.0 } else { m }
}

fn tint(palette: &[&str; 6], index: usize) -> String {
    palette
        .get(index.checked_rem(6).unwrap_or(0))
        .copied()
        .unwrap_or("#9be7ff")
        .to_owned()
}

fn seg_part(a: V, b: V, r0: f64, r1: f64, k: f64) -> Option<(Shape, V, V, V)> {
    let (wide, narrow, hi, lo) = if r0 >= r1 {
        (a, b, r0, r1)
    } else {
        (b, a, r1, r0)
    };
    let axis = sub(narrow, wide);
    let length = norm(axis);
    if length < 1e-9 {
        return None;
    }
    let [dx, dy, dz] = scale(axis, 1.0 / length);
    let rx = dy.clamp(-1.0, 1.0).acos().to_degrees();
    let ry = dx.atan2(dz).to_degrees();
    let mid = scale(add(wide, narrow), 0.5);
    let (shape, radius) = if hi > 0.0 && lo < 0.25 * hi {
        (Shape::Cone, hi)
    } else {
        (Shape::Cylinder, f64::midpoint(hi, lo))
    };
    let half = (length * 0.5 * k).clamp(0.01, 10.0);
    let r = (radius * k).clamp(0.01, 10.0);
    Some((shape, [r, half, r], scale(mid, k), [rx, ry, 0.0]))
}

pub fn compile(plan: &Plan) -> Result<Vec<Part>, FormaError> {
    compile_full(plan).map(|(parts, _)| parts)
}

pub fn compile_full(plan: &Plan) -> Result<(Vec<Part>, Vec<Label>), FormaError> {
    compile_scaled(plan).map(|(parts, labels, _)| (parts, labels))
}

pub fn compile_scaled(plan: &Plan) -> Result<(Vec<Part>, Vec<Label>, f64), FormaError> {
    let mut builder = Builder {
        nodes: 0,
        out: Vec::new(),
    };
    for node in &plan.nodes {
        builder.emit(node, 0)?;
    }
    let prims = builder.out;
    let extent = reach(&prims);
    if prims.is_empty() || extent <= 1e-9 {
        return Err(FormaError("empty"));
    }
    let k = REACH / extent;
    let colors = palette(&plan.theme);
    let mut parts = Vec::with_capacity(prims.len());
    let mut labels: Vec<Label> = Vec::new();
    for prim in &prims {
        match prim {
            Prim::Mark { name, at } => {
                if !labels.iter().any(|l| l.name == *name) {
                    labels.push(Label {
                        name: name.clone(),
                        at: scale(*at, k),
                    });
                }
            }
            Prim::Seg {
                a,
                b,
                r0,
                r1,
                color,
                weight,
            } => {
                if let Some((shape, size, at, rot)) = seg_part(*a, *b, *r0, *r1, k) {
                    parts.push(Part {
                        shape,
                        size,
                        at,
                        rot,
                        color: tint(&colors, *color),
                        weight: weight.clamp(0.05, 10.0),
                    });
                }
            }
            Prim::Blob {
                shape,
                at,
                size,
                rot,
                color,
                weight,
            } => parts.push(Part {
                shape: *shape,
                size: size.map(|v| (v * k).clamp(0.01, 10.0)),
                at: scale(*at, k),
                rot: rot.map(wrap),
                color: tint(&colors, *color),
                weight: weight.clamp(0.05, 10.0),
            }),
        }
    }
    if parts.is_empty() || parts.len() > MAX_PARTS {
        return Err(FormaError("too_many_parts"));
    }
    Ok((parts, labels, k))
}
