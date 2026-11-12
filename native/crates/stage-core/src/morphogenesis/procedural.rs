use std::f64::consts::TAU;

use super::taxonomy::{MorphoDescriptor, MorphologyKind, PaletteTheme};
use crate::particles::{Part, Shape, Spec};

fn make_part(
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

fn color_at(theme: PaletteTheme, idx: usize) -> &'static str {
    let colors = theme.colors();
    let safe_idx = idx.checked_rem_euclid(colors.len()).unwrap_or(0);
    colors.get(safe_idx).copied().unwrap_or("#5ef2ff")
}

pub fn generate_radial(desc: MorphoDescriptor) -> Spec {
    let colors = desc.theme.colors();
    let is_organism = desc.kind == MorphologyKind::RadialOrganism;
    let total_blades = desc.count.clamp(4, 10);
    let mut parts = Vec::with_capacity(usize::from(total_blades).saturating_add(4));

    let core_shape = if is_organism {
        Shape::Sphere
    } else {
        Shape::Cylinder
    };
    parts.push(make_part(
        core_shape,
        [1.3 * desc.aspect, 0.85, 1.3 * desc.aspect],
        [0.0, 0.85, 0.0],
        [0.0, 0.0, 0.0],
        colors.first().copied().unwrap_or("#5ef2ff"),
        2.4,
    ));
    parts.push(make_part(
        Shape::Torus,
        [1.25 * desc.aspect, 0.3, 1.25 * desc.aspect],
        [0.0, 0.45, 0.0],
        [0.0, 0.0, 0.0],
        color_at(desc.theme, 1),
        1.6,
    ));
    parts.push(make_part(
        Shape::Cone,
        [0.45, 1.15, 0.45],
        [0.0, -0.25, 0.0],
        [180.0, 0.0, 0.0],
        color_at(desc.theme, 2),
        1.4,
    ));

    let sat_shape = if is_organism {
        Shape::Helix
    } else {
        Shape::Box
    };
    for blade_idx in 0..total_blades {
        let fraction = f64::from(blade_idx) / f64::from(total_blades);
        let angle = fraction * TAU;
        let radius = 0.82 * desc.aspect;
        let pos_x = radius * angle.cos();
        let pos_z = radius * angle.sin();
        let rot_y = if is_organism {
            f64::from(blade_idx) * 30.0
        } else {
            -angle.to_degrees()
        };
        let blade_color = color_at(desc.theme, usize::from(blade_idx).saturating_add(3));
        parts.push(make_part(
            sat_shape,
            [0.18, 1.3, 0.18],
            [pos_x, -0.85, pos_z],
            [0.0, rot_y, 0.0],
            blade_color,
            1.1,
        ));
    }
    Spec { parts }
}

pub fn generate_bilateral(desc: MorphoDescriptor) -> Spec {
    let colors = desc.theme.colors();
    let is_vehicle = desc.kind == MorphologyKind::BilateralVehicle;
    let mut parts = Vec::with_capacity(10);

    let spine_shape = if is_vehicle {
        Shape::Cone
    } else {
        Shape::Cylinder
    };
    parts.push(make_part(
        spine_shape,
        [0.45, 1.6 * desc.aspect, 0.45],
        [0.0, 0.0, 0.0],
        [-90.0, 0.0, 0.0],
        colors.first().copied().unwrap_or("#ee9b00"),
        2.2,
    ));
    parts.push(make_part(
        Shape::Sphere,
        [0.55, 0.55, 0.55],
        [0.0, 0.1, 1.45 * desc.aspect],
        [0.0, 0.0, 0.0],
        color_at(desc.theme, 1),
        1.8,
    ));
    parts.push(make_part(
        Shape::Cone,
        [0.35, 0.75, 0.35],
        [0.0, 0.0, -1.55 * desc.aspect],
        [90.0, 0.0, 0.0],
        color_at(desc.theme, 2),
        1.3,
    ));

    for side in [-1.0_f64, 1.0_f64] {
        let wing_shape = if is_vehicle { Shape::Box } else { Shape::Helix };
        parts.push(make_part(
            wing_shape,
            [1.25, 0.12, 0.55],
            [side * 1.35, 0.05, 0.15],
            [0.0, side * -18.0, side * 8.0],
            color_at(desc.theme, 3),
            1.6,
        ));
        parts.push(make_part(
            Shape::Cone,
            [0.25, 0.85, 0.25],
            [side * 0.85, -0.45, -0.5],
            [-90.0, side * -15.0, 0.0],
            color_at(desc.theme, 4),
            1.2,
        ));
    }
    Spec { parts }
}

pub fn generate_orbital(desc: MorphoDescriptor) -> Spec {
    let colors = desc.theme.colors();
    let ring_count = desc.count.clamp(2, 5);
    let mut parts = Vec::with_capacity(usize::from(ring_count).saturating_mul(2).saturating_add(2));

    parts.push(make_part(
        Shape::Sphere,
        [0.85, 0.85, 0.85],
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        colors.first().copied().unwrap_or("#ffd166"),
        2.6,
    ));

    for ring_idx in 0..ring_count {
        let fraction = f64::from(ring_idx) / f64::from(ring_count);
        let radius = 1.35 + f64::from(ring_idx) * 0.45;
        let pitch = 25.0 + fraction * 40.0;
        let roll = -15.0 + fraction * 55.0;
        let ring_color = color_at(desc.theme, usize::from(ring_idx).saturating_add(1));
        parts.push(make_part(
            Shape::Torus,
            [radius, 0.18, radius],
            [0.0, 0.0, 0.0],
            [pitch, 0.0, roll],
            ring_color,
            1.5,
        ));
        let theta = fraction * TAU + 0.5;
        let sat_x = radius * theta.cos() * 0.85;
        let sat_y = radius * theta.sin() * 0.4;
        let sat_z = radius * (theta * 1.2).sin() * 0.75;
        parts.push(make_part(
            Shape::Sphere,
            [0.22, 0.22, 0.22],
            [sat_x, sat_y, sat_z],
            [0.0, 0.0, 0.0],
            color_at(desc.theme, usize::from(ring_idx).saturating_add(3)),
            0.9,
        ));
    }
    Spec { parts }
}

pub fn generate_helical(desc: MorphoDescriptor) -> Spec {
    let colors = desc.theme.colors();
    let mut parts = Vec::with_capacity(7);

    parts.push(make_part(
        Shape::Sphere,
        [0.45, 0.45, 0.45],
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        colors.first().copied().unwrap_or("#ff006e"),
        1.8,
    ));
    parts.push(make_part(
        Shape::Helix,
        [0.72, 1.85, 0.72],
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        color_at(desc.theme, 1),
        2.2,
    ));
    parts.push(make_part(
        Shape::Helix,
        [0.72, 1.85, 0.72],
        [0.0, 0.0, 0.0],
        [0.0, 180.0, 0.0],
        color_at(desc.theme, 2),
        2.2,
    ));
    parts.push(make_part(
        Shape::Torus,
        [1.35, 0.22, 1.35],
        [0.0, 0.0, 0.0],
        [32.0, 15.0, 0.0],
        color_at(desc.theme, 3),
        1.3,
    ));
    parts.push(make_part(
        Shape::Torus,
        [1.35, 0.22, 1.35],
        [0.0, 0.0, 0.0],
        [-32.0, -15.0, 0.0],
        color_at(desc.theme, 4),
        1.3,
    ));
    Spec { parts }
}

pub fn generate_branching(desc: MorphoDescriptor) -> Spec {
    let colors = desc.theme.colors();
    let branch_count = desc.count.clamp(3, 6);
    let mut parts = Vec::with_capacity(usize::from(branch_count).saturating_add(3));

    parts.push(make_part(
        Shape::Cylinder,
        [0.32, 1.5, 0.32],
        [0.0, -0.65, 0.0],
        [0.0, 0.0, 0.0],
        colors.first().copied().unwrap_or("#38b000"),
        2.2,
    ));
    parts.push(make_part(
        Shape::Sphere,
        [0.85, 0.75, 0.85],
        [0.0, 0.85, 0.0],
        [0.0, 0.0, 0.0],
        color_at(desc.theme, 1),
        2.0,
    ));

    for branch_idx in 0..branch_count {
        let fraction = f64::from(branch_idx) / f64::from(branch_count);
        let angle = fraction * TAU;
        let pos_x = 0.95 * angle.cos();
        let pos_z = 0.95 * angle.sin();
        let branch_color = color_at(desc.theme, usize::from(branch_idx).saturating_add(2));
        parts.push(make_part(
            Shape::Cone,
            [0.28, 0.95, 0.28],
            [pos_x, 0.75, pos_z],
            [angle.sin() * 25.0, 0.0, -angle.cos() * 25.0],
            branch_color,
            1.2,
        ));
    }
    Spec { parts }
}

pub fn generate_axial(desc: MorphoDescriptor) -> Spec {
    let colors = desc.theme.colors();
    let mut parts = Vec::with_capacity(6);

    parts.push(make_part(
        Shape::Cylinder,
        [0.55, 1.85, 0.55],
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        colors.first().copied().unwrap_or("#64dfdf"),
        2.4,
    ));
    parts.push(make_part(
        Shape::Cone,
        [0.55, 0.95, 0.55],
        [0.0, 1.75, 0.0],
        [0.0, 0.0, 0.0],
        color_at(desc.theme, 1),
        1.6,
    ));
    parts.push(make_part(
        Shape::Torus,
        [0.95, 0.22, 0.95],
        [0.0, -0.45, 0.0],
        [0.0, 0.0, 0.0],
        color_at(desc.theme, 2),
        1.4,
    ));
    parts.push(make_part(
        Shape::Cone,
        [0.72, 0.65, 0.72],
        [0.0, -1.65, 0.0],
        [180.0, 0.0, 0.0],
        color_at(desc.theme, 3),
        1.5,
    ));
    Spec { parts }
}

pub fn generate_polyhedral(desc: MorphoDescriptor) -> Spec {
    let colors = desc.theme.colors();
    let poly_count = desc.count.clamp(4, 8);
    let mut parts = Vec::with_capacity(usize::from(poly_count).saturating_add(2));

    parts.push(make_part(
        Shape::Sphere,
        [0.75, 0.75, 0.75],
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        colors.first().copied().unwrap_or("#2ec4b6"),
        2.4,
    ));
    parts.push(make_part(
        Shape::Torus,
        [1.35, 0.25, 1.35],
        [0.0, 0.0, 0.0],
        [45.0, 45.0, 0.0],
        color_at(desc.theme, 1),
        1.5,
    ));

    for poly_idx in 0..poly_count {
        let fraction = f64::from(poly_idx) / f64::from(poly_count);
        let theta = fraction * TAU;
        let phi = (f64::from(poly_idx) * 1.618_033_988_749_895).fract() * std::f64::consts::PI;
        let pos_x = 1.15 * phi.sin() * theta.cos();
        let pos_y = 1.15 * phi.cos();
        let pos_z = 1.15 * phi.sin() * theta.sin();
        let node_color = color_at(desc.theme, usize::from(poly_idx).saturating_add(2));
        parts.push(make_part(
            Shape::Box,
            [0.28, 0.28, 0.28],
            [pos_x, pos_y, pos_z],
            [theta.to_degrees(), phi.to_degrees(), 0.0],
            node_color,
            1.2,
        ));
    }
    Spec { parts }
}

pub fn generate_harmonic(desc: MorphoDescriptor) -> Spec {
    let colors = desc.theme.colors();
    let harm_count = desc.count.clamp(3, 6);
    let mut parts = Vec::with_capacity(usize::from(harm_count).saturating_add(3));

    let core_shape = match desc.seed % 3 {
        0 => Shape::Sphere,
        1 => Shape::Cylinder,
        _ => Shape::Cone,
    };
    parts.push(make_part(
        core_shape,
        [1.05 * desc.aspect, 1.05, 1.05 * desc.aspect],
        [0.0, 0.15, 0.0],
        [0.0, 0.0, 0.0],
        colors.first().copied().unwrap_or("#5ef2ff"),
        2.2,
    ));
    parts.push(make_part(
        Shape::Torus,
        [1.45 * desc.aspect, 0.28, 1.45 * desc.aspect],
        [0.0, 0.0, 0.0],
        [18.0, 0.0, -18.0],
        color_at(desc.theme, 1),
        1.7,
    ));
    parts.push(make_part(
        Shape::Cone,
        [0.5, 0.9, 0.5],
        [0.0, 1.15, 0.0],
        [0.0, 0.0, 0.0],
        color_at(desc.theme, 2),
        1.2,
    ));

    let sat_shape = match (desc.seed >> 4) % 4 {
        0 => Shape::Helix,
        1 => Shape::Cone,
        2 => Shape::Cylinder,
        _ => Shape::Sphere,
    };
    for harm_idx in 0..harm_count {
        let angle = (f64::from(harm_idx) / f64::from(harm_count)) * TAU;
        let radius = 1.15 * desc.aspect;
        let pos_x = radius * angle.cos();
        let pos_z = radius * angle.sin();
        let sat_color = color_at(desc.theme, usize::from(harm_idx).saturating_add(2));
        parts.push(make_part(
            sat_shape,
            [0.28, 0.95, 0.28],
            [pos_x, -0.45, pos_z],
            [0.0, f64::from(harm_idx) * 45.0, 0.0],
            sat_color,
            1.1,
        ));
    }
    Spec { parts }
}
