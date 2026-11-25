use serde_json::{Map, Value};

use crate::error::{HoloError, HoloResult};
use crate::model::{MAX_LAYER, MAX_PARTS, MOTIONS, Part, Scene, Shape};

const LIMIT: f32 = 10_000.0;
const MIN_HALF: f32 = 0.000_5;
const NAME_MAX: usize = 48;
const INFO_MAX: usize = 240;
const TITLE_MAX: usize = 64;
const PALETTE: [&str; 6] = [
    "#5ef2ff", "#9b7bff", "#66ffe3", "#ff7be5", "#7aa2ff", "#ffd166",
];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Source {
    Particles,
    Model,
}

pub fn scene(raw: &Value) -> HoloResult<Scene> {
    scene_limited(raw, MAX_PARTS)
}

pub fn scene_limited(raw: &Value, limit: usize) -> HoloResult<Scene> {
    let root = raw.as_object().ok_or(HoloError::BadJson)?;
    let source = match root.get("source").and_then(Value::as_str) {
        Some("particles") => Source::Particles,
        _ => Source::Model,
    };
    let items = root
        .get("parts")
        .and_then(Value::as_array)
        .ok_or(HoloError::NoParts)?;
    let parts: Vec<Part> = items
        .iter()
        .take(limit)
        .enumerate()
        .filter_map(|(index, item)| item.as_object().and_then(|map| part(map, source, index)))
        .collect();
    if parts.is_empty() {
        return Err(HoloError::NoParts);
    }
    Ok(Scene {
        title: text(root.get("title"), TITLE_MAX),
        euler: match source {
            Source::Particles => "ZYX",
            Source::Model => "XYZ",
        },
        parts,
        layers: 1,
        radius: 1.0,
    })
}

fn part(map: &Map<String, Value>, source: Source, index: usize) -> Option<Part> {
    let kind = map.get("shape").and_then(Value::as_str)?;
    let (shape, half, tube, soft) = match source {
        Source::Particles => particle_shape(kind, vec3(map.get("size"), 1.0)),
        Source::Model => model_shape(kind, map)?,
    };
    let at_key = if source == Source::Particles {
        "at"
    } else {
        "position"
    };
    let rot_key = if source == Source::Particles {
        "rot"
    } else {
        "rotation"
    };
    let name = text(map.get("name"), NAME_MAX);
    let label = text(map.get("label"), NAME_MAX);
    let layer = map.get("layer").and_then(Value::as_f64).map(layer_of);
    let metal = match map.get("metal") {
        Some(Value::Bool(true)) => 0.9,
        Some(value) => value.as_f64().map_or(0.1, |v| clamp(narrow(v), 0.0, 1.0)),
        None => 0.1,
    };
    Some(Part {
        label: if label.is_empty() {
            name.clone()
        } else {
            label
        },
        name,
        info: text(map.get("info"), INFO_MAX),
        shape,
        half: half.map(|v| v.max(MIN_HALF)),
        tube,
        at: vec3(map.get(at_key), 0.0),
        rot: vec3(map.get(rot_key), 0.0).map(|v| clamp(v, -360.0, 360.0)),
        color: color(map.get("color"), index),
        metal,
        rough: map
            .get("roughness")
            .and_then(Value::as_f64)
            .map_or(if metal > 0.5 { 0.22 } else { 0.55 }, |v| {
                clamp(narrow(v), 0.02, 1.0)
            }),
        soft,
        motion: motion(map.get("motion")),
        layer: layer.unwrap_or(0),
        layer_given: layer.is_some(),
        explode: [0.0; 3],
    })
}

fn particle_shape(kind: &str, s: [f32; 3]) -> (Shape, [f32; 3], f32, bool) {
    let [x, y, z] = s.map(f32::abs);
    match kind {
        "box" => (Shape::Box, [x, y, z], 0.0, false),
        "cylinder" => (Shape::Cylinder, [x, y, z], 0.0, false),
        "cone" => (Shape::Cone, [x, y, z], 0.0, false),
        "torus" => (Shape::Torus, [x, y * 0.26, z], 0.26, false),
        "helix" => (Shape::Helix, [x, y, z], 0.05, false),
        "spiral" => (Shape::Spiral, [x, (y * 0.04).max(0.01), z], 0.04, false),
        "plane" => (Shape::Box, [x, (y * 0.01).max(0.005), z], 0.0, false),
        "disc" => (Shape::Cylinder, [x, (y * 0.06).max(0.01), z], 0.0, false),
        "ring" => (Shape::Torus, [x, (y * 0.05).max(0.01), z], 0.19, false),
        "orbit" => (Shape::Torus, [x, (y * 0.02).max(0.005), z], 0.02, false),
        "cloud" | "halo" => (Shape::Sphere, [x, y, z], 0.0, true),
        _ => (Shape::Sphere, [x, y, z], 0.0, false),
    }
}

fn model_shape(kind: &str, map: &Map<String, Value>) -> Option<(Shape, [f32; 3], f32, bool)> {
    let r = ["radius", "radius_top", "radius_bottom"]
        .iter()
        .filter_map(|key| map.get(*key).and_then(Value::as_f64))
        .map(|v| clamp(narrow(v).abs(), 0.0, LIMIT))
        .fold(0.0_f32, f32::max)
        .max(MIN_HALF);
    let h = map
        .get("height")
        .and_then(Value::as_f64)
        .map_or(r * 2.0, |v| clamp(narrow(v).abs(), 0.0, LIMIT))
        * 0.5;
    let size = vec3(map.get("size"), 10.0).map(|v| v.abs() * 0.5);
    Some(match kind {
        "box" => (Shape::Box, size, 0.0, false),
        "wedge" => (Shape::Wedge, size, 0.0, false),
        "sphere" => (Shape::Sphere, [r, r, r], 0.0, false),
        "cylinder" => (Shape::Cylinder, [r, h, r], 0.0, false),
        "cone" => (Shape::Cone, [r, h, r], 0.0, false),
        "capsule" => (Shape::Capsule, [r, h.max(r), r], 0.0, false),
        "torus" => {
            let t = map
                .get("tube")
                .and_then(Value::as_f64)
                .map_or(r * 0.25, |v| clamp(narrow(v).abs(), MIN_HALF, LIMIT));
            let outer = r + t;
            (
                Shape::Torus,
                [outer, t, outer],
                clamp(t / outer, 0.02, 0.9),
                false,
            )
        }
        "helix" => (Shape::Helix, [r, h, r], 0.05, false),
        _ => return None,
    })
}

#[allow(clippy::cast_possible_truncation)]
fn narrow(value: f64) -> f32 {
    if value.is_finite() {
        value.clamp(-f64::from(LIMIT), f64::from(LIMIT)) as f32
    } else {
        0.0
    }
}

fn clamp(value: f32, lo: f32, hi: f32) -> f32 {
    if value.is_finite() {
        value.clamp(lo, hi)
    } else {
        lo
    }
}

fn vec3(value: Option<&Value>, default: f32) -> [f32; 3] {
    let Some(items) = value.and_then(Value::as_array) else {
        return [default; 3];
    };
    if items.len() != 3 {
        return [default; 3];
    }
    let mut out = [default; 3];
    for (slot, item) in out.iter_mut().zip(items) {
        *slot = item.as_f64().map_or(default, narrow);
    }
    out
}

#[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
fn layer_of(value: f64) -> u8 {
    if value.is_finite() {
        value.round().clamp(0.0, f64::from(MAX_LAYER)) as u8
    } else {
        0
    }
}

fn text(value: Option<&Value>, max: usize) -> String {
    value
        .and_then(Value::as_str)
        .unwrap_or_default()
        .chars()
        .filter(|c| !c.is_control() && !matches!(c, '<' | '>' | '"' | '`' | '\\'))
        .take(max)
        .collect::<String>()
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
}

fn color(value: Option<&Value>, index: usize) -> String {
    let given = value.and_then(Value::as_str).unwrap_or_default();
    let valid = given.len() == 7
        && given.starts_with('#')
        && given.chars().skip(1).all(|c| c.is_ascii_hexdigit());
    if valid {
        given.to_ascii_lowercase()
    } else {
        PALETTE
            .get(index.checked_rem(PALETTE.len()).unwrap_or(0))
            .copied()
            .unwrap_or("#5ef2ff")
            .to_owned()
    }
}

fn motion(value: Option<&Value>) -> &'static str {
    let wanted = value.and_then(Value::as_str).unwrap_or_default();
    MOTIONS
        .iter()
        .copied()
        .find(|m| *m == wanted)
        .unwrap_or("none")
}
