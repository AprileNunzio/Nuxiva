use serde::{Deserialize, Serialize};

use crate::particles::{Part, Shape, Spec};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GaussianSplat3D {
    pub center: [f64; 3],
    pub scale: [f64; 3],
    pub rotation_quat: [f64; 4],
    pub opacity: f64,
    pub base_rgb: [f64; 3],
    pub sh_directional: [f64; 9],
    pub roughness: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GaussianScene {
    pub concept: String,
    pub splats: Vec<GaussianSplat3D>,
    pub ambient_light: [f64; 3],
    pub key_light_dir: [f64; 3],
    pub exposure: f64,
}

fn parse_rgb_norm(hex: &str) -> [f64; 3] {
    let clean = hex.strip_prefix('#').unwrap_or("5ef2ff");
    let chan = |range: std::ops::Range<usize>| -> f64 {
        let byte = clean
            .get(range)
            .and_then(|s| u8::from_str_radix(s, 16).ok())
            .unwrap_or(180);
        f64::from(byte) / 255.0
    };
    [chan(0..2), chan(2..4), chan(4..6)]
}

fn euler_deg_to_quat(deg: [f64; 3]) -> [f64; 4] {
    let [rx, ry, rz] = deg.map(|d| (d * 0.5).to_radians());
    let (cx, sx) = (rx.cos(), rx.sin());
    let (cy, sy) = (ry.cos(), ry.sin());
    let (cz, sz) = (rz.cos(), rz.sin());
    [
        cx * cy * cz + sx * sy * sz,
        sx * cy * cz - cx * sy * sz,
        cx * sy * cz + sx * cy * sz,
        cx * cy * sz - sx * sy * cz,
    ]
}

fn subdivide_part_into_splats(part: &Part, subdiv: u8) -> Vec<GaussianSplat3D> {
    let count = subdiv.clamp(4, 32);
    let mut out = Vec::with_capacity(usize::from(count));
    let rgb = parse_rgb_norm(&part.color);
    let quat = euler_deg_to_quat(part.rot);
    let roughness = match part.shape {
        Shape::Sphere | Shape::Torus => 0.18,
        Shape::Cylinder | Shape::Cone => 0.28,
        Shape::Helix => 0.22,
        Shape::Box | Shape::Plane => 0.42,
    };

    for idx in 0..count {
        let t = f64::from(idx) / f64::from(count);
        let angle = t * std::f64::consts::TAU;
        let offset = match part.shape {
            Shape::Sphere => [
                part.size[0] * 0.45 * angle.cos(),
                part.size[1] * (2.0 * t - 1.0) * 0.45,
                part.size[2] * 0.45 * angle.sin(),
            ],
            Shape::Torus => [
                part.size[0] * 0.72 * angle.cos(),
                part.size[1] * 0.15 * (angle * 2.0).sin(),
                part.size[2] * 0.72 * angle.sin(),
            ],
            Shape::Helix => [
                part.size[0] * 0.65 * (angle * 2.0).cos(),
                part.size[1] * (2.0 * t - 1.0) * 0.75,
                part.size[2] * 0.65 * (angle * 2.0).sin(),
            ],
            _ => [
                part.size[0] * 0.35 * angle.cos(),
                part.size[1] * (2.0 * t - 1.0) * 0.55,
                part.size[2] * 0.35 * angle.sin(),
            ],
        };
        let center = [
            part.at[0] + offset[0],
            part.at[1] + offset[1],
            part.at[2] + offset[2],
        ];
        let scale = [
            (part.size[0] * 0.38).clamp(0.04, 2.5),
            (part.size[1] * 0.38).clamp(0.04, 2.5),
            (part.size[2] * 0.38).clamp(0.04, 2.5),
        ];
        let sh_directional = [
            rgb[0] * 0.35,
            rgb[1] * 0.35,
            rgb[2] * 0.35,
            0.18 * angle.cos(),
            0.22,
            0.18 * angle.sin(),
            0.12,
            0.15,
            0.24,
        ];
        out.push(GaussianSplat3D {
            center,
            scale,
            rotation_quat: quat,
            opacity: (part.weight * 0.42).clamp(0.25, 0.96),
            base_rgb: rgb,
            sh_directional,
            roughness,
        });
    }
    out
}

#[must_use]
pub fn synthesize_gaussian_scene(concept: &str, spec: &Spec, subdiv_per_part: u8) -> GaussianScene {
    let mut splats = Vec::new();
    for part in &spec.parts {
        splats.extend(subdivide_part_into_splats(part, subdiv_per_part));
    }
    GaussianScene {
        concept: concept.to_owned(),
        splats,
        ambient_light: [0.18, 0.24, 0.34],
        key_light_dir: [-0.45, 0.78, 0.42],
        exposure: 1.25,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::morphogenesis::synthesize_sculpture;

    #[test]
    fn builds_gaussian_splat_scene_with_sh_lighting() {
        let spec = synthesize_sculpture("medusa");
        let scene = synthesize_gaussian_scene("medusa", &spec, 12);
        assert_eq!(scene.concept, "medusa");
        assert!(scene.splats.len() >= 84);
        assert!(
            scene
                .splats
                .iter()
                .all(|s| s.opacity > 0.0 && s.opacity <= 1.0)
        );
    }
}
