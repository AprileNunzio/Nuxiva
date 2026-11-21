use serde::{Deserialize, Serialize};

pub const MAX_CSG_PARTS: usize = 64;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RenderFidelityTier {
    #[default]
    Particles,
    Mesh3d,
    PhotorealPbr,
}

impl RenderFidelityTier {
    #[must_use]
    pub const fn id(self) -> &'static str {
        match self {
            Self::Particles => "particles",
            Self::Mesh3d => "mesh_3d",
            Self::PhotorealPbr => "photoreal_pbr",
        }
    }

    #[must_use]
    pub fn from_id(id: &str) -> Option<Self> {
        match id.trim().to_ascii_lowercase().as_str() {
            "particles" | "particle" | "ologramma" | "hologram" => Some(Self::Particles),
            "mesh_3d" | "3d" | "mesh" | "solid" => Some(Self::Mesh3d),
            "photoreal_pbr" | "realistic" | "realistica" | "pbr" | "gta6" => {
                Some(Self::PhotorealPbr)
            }
            _ => None,
        }
    }

    #[must_use]
    pub const fn upgrade(self) -> Self {
        match self {
            Self::Particles => Self::Mesh3d,
            Self::Mesh3d | Self::PhotorealPbr => Self::PhotorealPbr,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CsgPrimitiveKind {
    Box,
    Cylinder,
    Cone,
    Sphere,
    Torus,
    Capsule,
    Wedge,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PbrMaterialSpec {
    pub base_color_hex: String,
    pub metallic: f32,
    pub roughness: f32,
    pub clearcoat: f32,
    pub emissive_intensity: f32,
    pub specular_tint: f32,
}

impl Default for PbrMaterialSpec {
    fn default() -> Self {
        Self {
            base_color_hex: "#22d3ee".to_owned(),
            metallic: 0.25,
            roughness: 0.45,
            clearcoat: 0.0,
            emissive_intensity: 0.0,
            specular_tint: 0.5,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CsgPrimitiveNode {
    pub name: String,
    pub kind: CsgPrimitiveKind,
    pub size: [f32; 3],
    pub position: [f32; 3],
    pub rotation_deg: [f32; 3],
    pub material: PbrMaterialSpec,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Generative3dAsset {
    pub subject: String,
    pub fidelity: RenderFidelityTier,
    pub nodes: Vec<CsgPrimitiveNode>,
    pub sun_azimuth_deg: f32,
    pub sun_elevation_deg: f32,
    pub bloom_strength: f32,
    pub ambient_occlusion: bool,
}

#[must_use]
pub fn synthesize_procedural_3d(subject: &str, fidelity: RenderFidelityTier) -> Generative3dAsset {
    let clean = subject.trim();
    let lower = clean.to_ascii_lowercase();
    let nodes = if lower.contains("macchina")
        || lower.contains("auto")
        || lower.contains("car")
        || lower.contains("veicol")
        || lower.contains("supercar")
    {
        build_supercar_csg()
    } else if lower.contains("drone") || lower.contains("aereo") || lower.contains("jet") {
        build_aerospace_csg()
    } else if lower.contains("casa") || lower.contains("edificio") || lower.contains("grattacielo")
    {
        build_architecture_csg()
    } else {
        build_parametric_sculpture_csg(clean)
    };

    let (bloom_strength, ambient_occlusion) = match fidelity {
        RenderFidelityTier::Particles => (0.65, false),
        RenderFidelityTier::Mesh3d => (0.25, true),
        RenderFidelityTier::PhotorealPbr => (0.85, true),
    };

    Generative3dAsset {
        subject: if clean.is_empty() {
            "hologram_object".to_owned()
        } else {
            clean.chars().take(64).collect()
        },
        fidelity,
        nodes,
        sun_azimuth_deg: 135.0,
        sun_elevation_deg: 24.0,
        bloom_strength,
        ambient_occlusion,
    }
}

fn pbr(
    color: &str,
    metallic: f32,
    roughness: f32,
    clearcoat: f32,
    emissive: f32,
) -> PbrMaterialSpec {
    PbrMaterialSpec {
        base_color_hex: color.to_owned(),
        metallic: metallic.clamp(0.0, 1.0),
        roughness: roughness.clamp(0.02, 1.0),
        clearcoat: clearcoat.clamp(0.0, 1.0),
        emissive_intensity: emissive.clamp(0.0, 5.0),
        specular_tint: 0.85,
    }
}

fn node(
    name: &str,
    kind: CsgPrimitiveKind,
    size: [f32; 3],
    position: [f32; 3],
    rotation_deg: [f32; 3],
    material: PbrMaterialSpec,
) -> CsgPrimitiveNode {
    CsgPrimitiveNode {
        name: name.to_owned(),
        kind,
        size,
        position,
        rotation_deg,
        material,
    }
}

fn build_supercar_csg() -> Vec<CsgPrimitiveNode> {
    let mut nodes = build_supercar_body_csg();
    nodes.extend(build_supercar_wheels_and_lights_csg());
    nodes
}

fn build_supercar_body_csg() -> Vec<CsgPrimitiveNode> {
    let paint = pbr("#e11d48", 0.88, 0.14, 0.96, 0.0);
    let glass = pbr("#0f172a", 0.15, 0.05, 1.0, 0.0);
    let carbon = pbr("#1e293b", 0.45, 0.32, 0.35, 0.0);
    vec![
        node(
            "chassis_lower",
            CsgPrimitiveKind::Box,
            [1.92, 0.36, 4.35],
            [0.0, -0.12, 0.0],
            [0.0, 0.0, 0.0],
            paint.clone(),
        ),
        node(
            "hood_wedge",
            CsgPrimitiveKind::Wedge,
            [1.86, 0.32, 1.45],
            [0.0, 0.08, 1.35],
            [0.0, 0.0, 0.0],
            paint.clone(),
        ),
        node(
            "cabin_canopy",
            CsgPrimitiveKind::Capsule,
            [1.52, 0.48, 1.95],
            [0.0, 0.24, -0.15],
            [0.0, 0.0, 0.0],
            glass,
        ),
        node(
            "rear_deck",
            CsgPrimitiveKind::Box,
            [1.90, 0.34, 1.25],
            [0.0, 0.08, -1.42],
            [0.0, 0.0, 0.0],
            paint,
        ),
        node(
            "rear_spoiler",
            CsgPrimitiveKind::Box,
            [1.84, 0.06, 0.32],
            [0.0, 0.38, -1.96],
            [-8.0, 0.0, 0.0],
            carbon,
        ),
    ]
}

fn build_supercar_wheels_and_lights_csg() -> Vec<CsgPrimitiveNode> {
    let tire = pbr("#111827", 0.08, 0.82, 0.0, 0.0);
    let rim = pbr("#cbd5e1", 0.95, 0.18, 0.5, 0.0);
    let head = pbr("#e0f2fe", 0.1, 0.1, 0.5, 2.8);
    let tail = pbr("#ff1e42", 0.1, 0.1, 0.5, 2.5);
    vec![
        node(
            "wheel_fl",
            CsgPrimitiveKind::Cylinder,
            [0.36, 0.26, 0.36],
            [-0.96, -0.24, 1.32],
            [0.0, 0.0, 90.0],
            tire.clone(),
        ),
        node(
            "wheel_fr",
            CsgPrimitiveKind::Cylinder,
            [0.36, 0.26, 0.36],
            [0.96, -0.24, 1.32],
            [0.0, 0.0, 90.0],
            tire.clone(),
        ),
        node(
            "wheel_rl",
            CsgPrimitiveKind::Cylinder,
            [0.38, 0.28, 0.38],
            [-0.98, -0.22, -1.32],
            [0.0, 0.0, 90.0],
            tire.clone(),
        ),
        node(
            "wheel_rr",
            CsgPrimitiveKind::Cylinder,
            [0.38, 0.28, 0.38],
            [0.98, -0.22, -1.32],
            [0.0, 0.0, 90.0],
            tire,
        ),
        node(
            "rim_fl",
            CsgPrimitiveKind::Cylinder,
            [0.24, 0.28, 0.24],
            [-0.97, -0.24, 1.32],
            [0.0, 0.0, 90.0],
            rim.clone(),
        ),
        node(
            "rim_fr",
            CsgPrimitiveKind::Cylinder,
            [0.24, 0.28, 0.24],
            [0.97, -0.24, 1.32],
            [0.0, 0.0, 90.0],
            rim.clone(),
        ),
        node(
            "rim_rl",
            CsgPrimitiveKind::Cylinder,
            [0.25, 0.30, 0.25],
            [-0.99, -0.22, -1.32],
            [0.0, 0.0, 90.0],
            rim.clone(),
        ),
        node(
            "rim_rr",
            CsgPrimitiveKind::Cylinder,
            [0.25, 0.30, 0.25],
            [0.99, -0.22, -1.32],
            [0.0, 0.0, 90.0],
            rim,
        ),
        node(
            "headlight_l",
            CsgPrimitiveKind::Box,
            [0.36, 0.08, 0.12],
            [-0.68, 0.02, 2.14],
            [0.0, 0.0, 0.0],
            head.clone(),
        ),
        node(
            "headlight_r",
            CsgPrimitiveKind::Box,
            [0.36, 0.08, 0.12],
            [0.68, 0.02, 2.14],
            [0.0, 0.0, 0.0],
            head,
        ),
        node(
            "taillight_bar",
            CsgPrimitiveKind::Box,
            [1.68, 0.07, 0.10],
            [0.0, 0.12, -2.14],
            [0.0, 0.0, 0.0],
            tail,
        ),
    ]
}

fn build_aerospace_csg() -> Vec<CsgPrimitiveNode> {
    let titanium = pbr("#94a3b8", 0.92, 0.22, 0.75, 0.0);
    let thruster = pbr("#38bdf8", 0.2, 0.1, 0.4, 2.6);
    vec![
        node(
            "fuselage",
            CsgPrimitiveKind::Capsule,
            [0.65, 0.55, 3.6],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            titanium.clone(),
        ),
        node(
            "wing_main",
            CsgPrimitiveKind::Box,
            [3.8, 0.09, 0.95],
            [0.0, 0.0, -0.2],
            [0.0, 0.0, 0.0],
            titanium.clone(),
        ),
        node(
            "tail_fin",
            CsgPrimitiveKind::Wedge,
            [0.12, 0.75, 0.85],
            [0.0, 0.42, -1.35],
            [0.0, 0.0, 0.0],
            titanium,
        ),
        node(
            "engine_glow",
            CsgPrimitiveKind::Cylinder,
            [0.35, 0.35, 0.35],
            [0.0, 0.0, -1.85],
            [90.0, 0.0, 0.0],
            thruster,
        ),
    ]
}

fn build_architecture_csg() -> Vec<CsgPrimitiveNode> {
    let concrete = pbr("#cbd5e1", 0.15, 0.65, 0.2, 0.0);
    let glass = pbr("#38bdf8", 0.85, 0.08, 1.0, 0.4);
    vec![
        node(
            "podium",
            CsgPrimitiveKind::Box,
            [2.4, 0.45, 2.4],
            [0.0, -0.75, 0.0],
            [0.0, 0.0, 0.0],
            concrete,
        ),
        node(
            "tower_core",
            CsgPrimitiveKind::Box,
            [1.35, 2.4, 1.35],
            [0.0, 0.45, 0.0],
            [0.0, 0.0, 0.0],
            glass.clone(),
        ),
        node(
            "crown_spire",
            CsgPrimitiveKind::Cone,
            [0.75, 0.85, 0.75],
            [0.0, 1.95, 0.0],
            [0.0, 0.0, 0.0],
            glass,
        ),
    ]
}

fn build_parametric_sculpture_csg(subject: &str) -> Vec<CsgPrimitiveNode> {
    let seed = subject.bytes().fold(0x811c_9dc5_u32, |acc, b| {
        acc.wrapping_mul(33) ^ u32::from(b)
    });
    let r = u8::try_from(seed & 0xFF).unwrap_or(64).clamp(40, 240);
    let g = u8::try_from((seed >> 8) & 0xFF)
        .unwrap_or(180)
        .clamp(60, 245);
    let b = u8::try_from((seed >> 16) & 0xFF)
        .unwrap_or(230)
        .clamp(90, 250);
    let hex = format!("#{r:02x}{g:02x}{b:02x}");
    let core_mat = pbr(&hex, 0.85, 0.16, 0.92, 0.35);
    let ring_mat = pbr("#38bdf8", 0.92, 0.12, 0.95, 0.85);
    vec![
        node(
            "core_body",
            CsgPrimitiveKind::Sphere,
            [1.15, 1.15, 1.15],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            core_mat.clone(),
        ),
        node(
            "orbital_ring_a",
            CsgPrimitiveKind::Torus,
            [1.65, 0.16, 1.65],
            [0.0, 0.0, 0.0],
            [25.0, 0.0, 15.0],
            ring_mat.clone(),
        ),
        node(
            "orbital_ring_b",
            CsgPrimitiveKind::Torus,
            [1.35, 0.12, 1.35],
            [0.0, 0.0, 0.0],
            [-35.0, 45.0, 0.0],
            ring_mat,
        ),
        node(
            "pedestal",
            CsgPrimitiveKind::Cylinder,
            [1.1, 0.25, 1.1],
            [0.0, -0.95, 0.0],
            [0.0, 0.0, 0.0],
            core_mat,
        ),
    ]
}
