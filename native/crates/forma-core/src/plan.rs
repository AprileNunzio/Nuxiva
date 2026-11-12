use serde::{Deserialize, Serialize};
use std::fmt;

pub const MAX_PARTS: usize = 96;
pub const MAX_PRIMS: usize = 256;
pub const MAX_NODES: usize = 128;
pub const MAX_DEPTH: usize = 5;
pub const MAX_PROFILE: usize = 16;
pub const MAX_STEPS: usize = 12;
pub const MAX_COUNT: usize = 24;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct FormaError(pub &'static str);

impl fmt::Display for FormaError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.0)
    }
}

impl std::error::Error for FormaError {}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Axis {
    #[default]
    X,
    Y,
    Z,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum PathKind {
    #[default]
    Line,
    Arc,
    Wave,
    Spiral,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Shape {
    #[default]
    Sphere,
    Box,
    Cylinder,
    Cone,
    Torus,
    Helix,
    Plane,
    Cloud,
    Disc,
    Spiral,
    Ring,
    Halo,
    Orbit,
}

const fn one() -> f64 {
    1.0
}

const fn unit() -> [f64; 3] {
    [1.0, 1.0, 1.0]
}

const fn up() -> [f64; 3] {
    [0.0, 1.0, 0.0]
}

const fn steps() -> usize {
    4
}

const fn radius() -> f64 {
    0.1
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "op", rename_all = "lowercase", deny_unknown_fields)]
pub enum Node {
    Lathe {
        profile: Vec<[f64; 2]>,
        #[serde(default)]
        color: usize,
        #[serde(default = "one")]
        weight: f64,
    },
    Sweep {
        #[serde(default)]
        path: PathKind,
        #[serde(default)]
        from: [f64; 3],
        #[serde(default = "up")]
        dir: [f64; 3],
        #[serde(default = "one")]
        length: f64,
        #[serde(default)]
        bend: f64,
        #[serde(default = "radius")]
        r0: f64,
        #[serde(default = "radius")]
        r1: f64,
        #[serde(default = "steps")]
        steps: usize,
        #[serde(default)]
        color: usize,
        #[serde(default = "one")]
        weight: f64,
    },
    Blob {
        #[serde(default)]
        shape: Shape,
        #[serde(default)]
        at: [f64; 3],
        #[serde(default = "unit")]
        size: [f64; 3],
        #[serde(default)]
        rot: [f64; 3],
        #[serde(default)]
        color: usize,
        #[serde(default = "one")]
        weight: f64,
    },
    Radial {
        count: usize,
        #[serde(default)]
        radius: f64,
        #[serde(default)]
        phase: f64,
        child: Box<Node>,
    },
    Mirror {
        axis: Axis,
        child: Box<Node>,
    },
    Rotate {
        axis: Axis,
        deg: f64,
        child: Box<Node>,
    },
    Group {
        children: Vec<Node>,
    },
    Mark {
        name: String,
        at: [f64; 3],
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Plan {
    #[serde(default = "default_theme")]
    pub theme: String,
    pub nodes: Vec<Node>,
}

fn default_theme() -> String {
    "ethereal".to_owned()
}
