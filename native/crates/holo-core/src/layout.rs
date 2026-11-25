use crate::model::{MAX_LAYER, Part, Scene};

const CORE: f32 = 0.05;
const NEST: f32 = 1.5;

#[must_use]
pub fn arrange(mut scene: Scene) -> Scene {
    normalize(&mut scene.parts);
    let depths: Vec<u8> = if scene.parts.iter().any(|p| p.layer_given) {
        scene.parts.iter().map(|p| p.layer.min(MAX_LAYER)).collect()
    } else {
        scene
            .parts
            .iter()
            .map(|inner| depth(inner, &scene.parts))
            .collect()
    };
    for (part, layer) in scene.parts.iter_mut().zip(depths) {
        part.layer = layer;
    }
    let deepest = scene.parts.iter().map(|p| p.layer).max().unwrap_or(0);
    scene.layers = deepest.saturating_add(1);
    for part in &mut scene.parts {
        part.explode = explode(part);
    }
    scene.radius = 1.0;
    scene
}

fn reach(part: &Part) -> [f32; 3] {
    if part.rot.iter().any(|r| r.abs() > 0.5) {
        let r = part.half.iter().copied().fold(0.0_f32, f32::max);
        [r; 3]
    } else {
        part.half
    }
}

fn normalize(parts: &mut [Part]) {
    let mut lo = [f32::MAX; 3];
    let mut hi = [f32::MIN; 3];
    for part in parts.iter() {
        let span = reach(part);
        for ((l, h), (c, s)) in lo
            .iter_mut()
            .zip(hi.iter_mut())
            .zip(part.at.iter().zip(span.iter()))
        {
            *l = l.min(c - s);
            *h = h.max(c + s);
        }
    }
    let mut center = [0.0_f32; 3];
    let mut extent = 0.0_f32;
    for ((c, l), h) in center.iter_mut().zip(lo).zip(hi) {
        *c = f32::midpoint(l, h);
        extent = extent.max((h - l) * 0.5);
    }
    let scale = if extent.is_finite() && extent > f32::EPSILON {
        1.0 / extent
    } else {
        1.0
    };
    for part in parts.iter_mut() {
        for (a, c) in part.at.iter_mut().zip(center) {
            *a = (*a - c) * scale;
        }
        for h in &mut part.half {
            *h *= scale;
        }
    }
}

fn volume(part: &Part) -> f32 {
    part.half.iter().product()
}

fn contains(outer: &Part, point: [f32; 3]) -> bool {
    let span = reach(outer);
    outer
        .at
        .iter()
        .zip(span.iter())
        .zip(point.iter())
        .all(|((c, s), p)| (p - c).abs() < *s)
}

fn depth(inner: &Part, all: &[Part]) -> u8 {
    let own = volume(inner);
    let count = all
        .iter()
        .filter(|outer| {
            !std::ptr::eq(*outer, inner) && volume(outer) > own * NEST && contains(outer, inner.at)
        })
        .count();
    u8::try_from(count).unwrap_or(MAX_LAYER).min(MAX_LAYER)
}

fn explode(part: &Part) -> [f32; 3] {
    let length = part.at.iter().map(|v| v * v).sum::<f32>().sqrt();
    if length < CORE {
        return [0.0; 3];
    }
    let push = 0.35 + 0.15 * f32::from(part.layer);
    part.at.map(|v| v / length * push)
}
