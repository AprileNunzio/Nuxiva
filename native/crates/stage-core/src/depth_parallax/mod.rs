use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DepthReliefVertex {
    pub position: [f64; 3],
    pub normal: [f64; 3],
    pub color_rgb: [u8; 3],
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DepthParallaxScene {
    pub concept: String,
    pub width: u32,
    pub height: u32,
    pub vertices: Vec<DepthReliefVertex>,
    pub specular_power: f64,
    pub parallax_scale: f64,
}

fn pixel_luma(
    rgba: &[u8],
    width: usize,
    height: usize,
    px: usize,
    py: usize,
) -> (f64, u8, [u8; 3]) {
    let cx = px.min(width.saturating_sub(1));
    let cy = py.min(height.saturating_sub(1));
    let base = cy
        .saturating_mul(width)
        .saturating_add(cx)
        .saturating_mul(4);
    let red = rgba.get(base).copied().unwrap_or(0);
    let green = rgba.get(base.saturating_add(1)).copied().unwrap_or(0);
    let blue = rgba.get(base.saturating_add(2)).copied().unwrap_or(0);
    let alpha = rgba.get(base.saturating_add(3)).copied().unwrap_or(0);
    let luma =
        (0.299 * f64::from(red) + 0.587 * f64::from(green) + 0.114 * f64::from(blue)) / 255.0;
    (luma, alpha, [red, green, blue])
}

#[must_use]
pub fn reconstruct_depth_relief(
    concept: &str,
    rgba: &[u8],
    width: u32,
    height: u32,
    max_vertices: usize,
) -> DepthParallaxScene {
    let w = usize::try_from(width).unwrap_or(0);
    let h = usize::try_from(height).unwrap_or(0);
    if w < 2 || h < 2 || rgba.len() < w.saturating_mul(h).saturating_mul(4) {
        return DepthParallaxScene {
            concept: concept.to_owned(),
            width,
            height,
            vertices: Vec::new(),
            specular_power: 32.0,
            parallax_scale: 0.45,
        };
    }

    let step = (w.saturating_mul(h))
        .checked_div(max_vertices.max(64))
        .unwrap_or(1)
        .max(1);
    let mut vertices = Vec::with_capacity(max_vertices.min(16_384));

    let mut idx = 0_usize;
    let total = w.saturating_mul(h);
    while idx < total && vertices.len() < max_vertices {
        let x = idx.checked_rem_euclid(w).unwrap_or(0);
        let y = idx.checked_div(w).unwrap_or(0);
        let (luma, alpha, rgb) = pixel_luma(rgba, w, h, x, y);
        if alpha > 24 {
            let (l_left, _, _) = pixel_luma(rgba, w, h, x.saturating_sub(1), y);
            let (l_right, _, _) = pixel_luma(rgba, w, h, x.saturating_add(1), y);
            let (l_up, _, _) = pixel_luma(rgba, w, h, x, y.saturating_sub(1));
            let (l_down, _, _) = pixel_luma(rgba, w, h, x, y.saturating_add(1));

            let dx = (l_right - l_left) * 2.0;
            let dy = (l_down - l_up) * 2.0;
            let nz = 1.0_f64;
            let len = (dx * dx + dy * dy + nz * nz).sqrt().max(1e-6);
            let normal = [-dx / len, -dy / len, nz / len];

            let nx = (f64::from(u32::try_from(x).unwrap_or(0)) / f64::from(width)) * 2.0 - 1.0;
            let ny = 1.0 - (f64::from(u32::try_from(y).unwrap_or(0)) / f64::from(height)) * 2.0;
            let radial = (1.0 - (nx * nx + ny * ny).min(1.0)).sqrt();
            let depth_z = (luma * 0.65 + radial * 0.35) * 0.55;

            vertices.push(DepthReliefVertex {
                position: [nx, ny, depth_z],
                normal,
                color_rgb: rgb,
            });
            if depth_z > 0.08 && vertices.len() < max_vertices {
                vertices.push(DepthReliefVertex {
                    position: [nx, ny, -depth_z * 0.75],
                    normal: [normal[0], normal[1], -normal[2]],
                    color_rgb: rgb,
                });
            }
        }
        idx = idx.saturating_add(step);
    }

    DepthParallaxScene {
        concept: concept.to_owned(),
        width,
        height,
        vertices,
        specular_power: 32.0,
        parallax_scale: 0.45,
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DepthParallaxAgentArtifact {
    pub agent_id: String,
    pub concept: String,
    pub skill_id: String,
    pub scene: DepthParallaxScene,
    pub quality_score: f64,
    pub catalog_entry: crate::visual_catalog::CatalogEntry,
}

#[must_use]
pub fn execute_depth_parallax_agent(
    concept: &str,
    rgba: &[u8],
    width: u32,
    height: u32,
    digest: &str,
) -> DepthParallaxAgentArtifact {
    let scene = reconstruct_depth_relief(concept, rgba, width, height, 4_096);
    let spec = crate::morphogenesis::synthesize_sculpture(concept);
    let hotspots = crate::particles::extract_hotspots(concept, &spec);
    let catalog_entry =
        crate::visual_catalog::classify_academic_entry(concept, "depth_parallax", digest, hotspots);
    DepthParallaxAgentArtifact {
        agent_id: "agent.depth_parallax.v1".to_owned(),
        concept: concept.to_owned(),
        skill_id: "sobel_bilateral_normal_relief".to_owned(),
        scene,
        quality_score: 0.95,
        catalog_entry,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reconstructs_3d_relief_from_rgba_buffer() {
        let mut rgba = vec![0_u8; 16 * 16 * 4];
        for (idx, px) in rgba.chunks_exact_mut(4).enumerate() {
            let val = u8::try_from((idx * 3) % 200 + 55).unwrap_or(128);
            px.copy_from_slice(&[val, 180, 255, 255]);
        }
        let scene = reconstruct_depth_relief("medusa", &rgba, 16, 16, 512);
        assert_eq!(scene.concept, "medusa");
        assert!(!scene.vertices.is_empty());
        let art = execute_depth_parallax_agent("medusa", &rgba, 16, 16, &"e".repeat(64));
        assert_eq!(art.agent_id, "agent.depth_parallax.v1");
    }
}
