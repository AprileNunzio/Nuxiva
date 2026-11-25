use serde::Serialize;

pub const MAX_PARTS: usize = 96;
pub const MAX_LAYER: u8 = 7;
pub const MOTIONS: [&str; 5] = ["none", "spin", "pulse", "orbit", "sway"];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Shape {
    Box,
    Wedge,
    Sphere,
    Cylinder,
    Cone,
    Capsule,
    Torus,
    Helix,
    Spiral,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Part {
    pub name: String,
    pub label: String,
    pub info: String,
    pub shape: Shape,
    pub half: [f32; 3],
    pub tube: f32,
    pub at: [f32; 3],
    pub rot: [f32; 3],
    pub color: String,
    pub metal: f32,
    pub rough: f32,
    pub soft: bool,
    pub motion: &'static str,
    pub layer: u8,
    pub explode: [f32; 3],
    #[serde(skip)]
    pub layer_given: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Scene {
    pub title: String,
    pub euler: &'static str,
    pub parts: Vec<Part>,
    pub layers: u8,
    pub radius: f32,
}
