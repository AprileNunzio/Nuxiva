use std::f64::consts::TAU;

use crate::particles::{Part, Shape, Spec};

fn part(
    shape: Shape,
    size: [f64; 3],
    at: [f64; 3],
    rot: [f64; 3],
    color: &str,
    weight: f64,
) -> Part {
    Part {
        shape,
        size,
        at,
        rot,
        color: color.to_owned(),
        weight,
    }
}

pub(super) fn medusa_spec() -> Spec {
    let mut parts = vec![
        part(
            Shape::Sphere,
            [1.35, 0.85, 1.35],
            [0.0, 0.95, 0.0],
            [0.0, 0.0, 0.0],
            "#5ef2ff",
            2.4,
        ),
        part(
            Shape::Torus,
            [1.22, 0.32, 1.22],
            [0.0, 0.45, 0.0],
            [0.0, 0.0, 0.0],
            "#a87bff",
            1.6,
        ),
        part(
            Shape::Sphere,
            [0.68, 0.48, 0.68],
            [0.0, 0.82, 0.0],
            [0.0, 0.0, 0.0],
            "#ff7be5",
            1.3,
        ),
        part(
            Shape::Cone,
            [0.42, 1.1, 0.42],
            [0.0, -0.35, 0.0],
            [180.0, 0.0, 0.0],
            "#c49bff",
            1.5,
        ),
    ];
    for i in 0..6_u8 {
        let angle = (f64::from(i) / 6.0) * TAU;
        let x = 0.78 * angle.cos();
        let z = 0.78 * angle.sin();
        let color = if i.is_multiple_of(2) {
            "#4ce6ff"
        } else {
            "#8c6bff"
        };
        parts.push(part(
            Shape::Helix,
            [0.16, 1.35, 0.16],
            [x, -0.85, z],
            [0.0, f64::from(i) * 30.0, 0.0],
            color,
            1.1,
        ));
    }
    Spec { parts }
}

pub(super) fn molecular_spec() -> Spec {
    Spec {
        parts: vec![
            part(
                Shape::Sphere,
                [0.55, 0.55, 0.55],
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0],
                "#ff6bd6",
                2.0,
            ),
            part(
                Shape::Helix,
                [0.75, 1.85, 0.75],
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0],
                "#4cf2ff",
                2.2,
            ),
            part(
                Shape::Helix,
                [0.75, 1.85, 0.75],
                [0.0, 0.0, 0.0],
                [0.0, 180.0, 0.0],
                "#9b7bff",
                2.2,
            ),
            part(
                Shape::Torus,
                [1.45, 0.25, 1.45],
                [0.0, 0.0, 0.0],
                [35.0, 20.0, 0.0],
                "#66ffe3",
                1.4,
            ),
            part(
                Shape::Torus,
                [1.45, 0.25, 1.45],
                [0.0, 0.0, 0.0],
                [-35.0, -20.0, 0.0],
                "#7aa2ff",
                1.4,
            ),
        ],
    }
}

pub(super) fn cosmic_spec() -> Spec {
    Spec {
        parts: vec![
            part(
                Shape::Sphere,
                [0.95, 0.95, 0.95],
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0],
                "#ffd166",
                2.5,
            ),
            part(
                Shape::Torus,
                [1.85, 0.22, 1.85],
                [0.0, 0.0, 0.0],
                [22.0, 0.0, 12.0],
                "#5ce1e6",
                2.0,
            ),
            part(
                Shape::Torus,
                [2.35, 0.16, 2.35],
                [0.0, 0.0, 0.0],
                [22.0, 0.0, 12.0],
                "#9b7bff",
                1.5,
            ),
            part(
                Shape::Cone,
                [0.25, 1.4, 0.25],
                [0.0, 1.2, 0.0],
                [0.0, 0.0, 0.0],
                "#72efdd",
                0.9,
            ),
            part(
                Shape::Cone,
                [0.25, 1.4, 0.25],
                [0.0, -1.2, 0.0],
                [180.0, 0.0, 0.0],
                "#72efdd",
                0.9,
            ),
        ],
    }
}

pub(super) fn mechanical_spec() -> Spec {
    Spec {
        parts: vec![
            part(
                Shape::Cylinder,
                [0.65, 1.55, 0.65],
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 90.0],
                "#64dfdf",
                2.2,
            ),
            part(
                Shape::Torus,
                [1.05, 0.3, 1.05],
                [-0.85, 0.0, 0.0],
                [0.0, 0.0, 90.0],
                "#48bfe3",
                1.6,
            ),
            part(
                Shape::Torus,
                [1.05, 0.3, 1.05],
                [0.85, 0.0, 0.0],
                [0.0, 0.0, 90.0],
                "#48bfe3",
                1.6,
            ),
            part(
                Shape::Cone,
                [0.65, 0.75, 0.65],
                [1.75, 0.0, 0.0],
                [0.0, 0.0, -90.0],
                "#80ffdb",
                1.3,
            ),
            part(
                Shape::Sphere,
                [0.48, 0.48, 0.48],
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0],
                "#ff9f1c",
                1.5,
            ),
            part(
                Shape::Box,
                [0.35, 0.08, 1.95],
                [0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0],
                "#7400b8",
                1.4,
            ),
        ],
    }
}

pub(super) fn universal_hash_spec(concept: &str) -> Spec {
    let mut h: u64 = 0xCBF2_9CE4_8422_2325;
    for b in concept.bytes() {
        h ^= u64::from(b);
        h = h.wrapping_mul(0x0100_0000_01B3);
    }
    let palette = [
        "#5ef2ff", "#9b7bff", "#66ffe3", "#ff7be5", "#7aa2ff", "#ffd166",
    ];
    let core_shape = match h % 3 {
        0 => Shape::Sphere,
        1 => Shape::Cylinder,
        _ => Shape::Cone,
    };
    let sat_shape = match (h >> 4) % 4 {
        0 => Shape::Helix,
        1 => Shape::Cone,
        2 => Shape::Cylinder,
        _ => Shape::Sphere,
    };
    let mut parts = vec![
        part(
            core_shape,
            [1.05, 1.05, 1.05],
            [0.0, 0.15, 0.0],
            [0.0, 0.0, 0.0],
            palette.first().copied().unwrap_or("#5ef2ff"),
            2.2,
        ),
        part(
            Shape::Torus,
            [1.45, 0.28, 1.45],
            [0.0, 0.0, 0.0],
            [18.0, 0.0, -18.0],
            palette.get(1).copied().unwrap_or("#9b7bff"),
            1.7,
        ),
        part(
            Shape::Cone,
            [0.5, 0.9, 0.5],
            [0.0, 1.15, 0.0],
            [0.0, 0.0, 0.0],
            palette.get(2).copied().unwrap_or("#66ffe3"),
            1.2,
        ),
    ];
    for i in 0..4_u8 {
        let angle = (f64::from(i) / 4.0) * TAU;
        let radius = 1.15;
        let x = radius * angle.cos();
        let z = radius * angle.sin();
        let idx = usize::from(i)
            .saturating_add(2)
            .checked_rem_euclid(palette.len())
            .unwrap_or(0);
        let color = palette.get(idx).copied().unwrap_or("#5ef2ff");
        parts.push(part(
            sat_shape,
            [0.28, 0.95, 0.28],
            [x, -0.45, z],
            [0.0, f64::from(i) * 45.0, 0.0],
            color,
            1.1,
        ));
    }
    Spec { parts }
}
