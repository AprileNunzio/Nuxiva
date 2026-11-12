use serde::{Deserialize, Serialize};
use std::f64::consts::TAU;

use crate::plan::{Axis, MAX_COUNT, Node, PathKind, Plan, Shape};

const SAMPLES: u32 = 8;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Traits {
    pub symmetry: String,
    pub body: String,
    pub length: f64,
    pub width: f64,
    pub limb: String,
    pub limbs: u32,
    pub limb_length: f64,
    pub curl: f64,
    pub rings: u32,
    pub theme: String,
}

impl Default for Traits {
    fn default() -> Self {
        Self {
            symmetry: "radial".to_owned(),
            body: "sphere".to_owned(),
            length: 1.5,
            width: 1.0,
            limb: "spread".to_owned(),
            limbs: 4,
            limb_length: 1.0,
            curl: 0.0,
            rings: 0,
            theme: "ethereal".to_owned(),
        }
    }
}

#[must_use]
pub fn schema() -> serde_json::Value {
    serde_json::json!({
        "fields": [
            {"name": "symmetry", "kind": "string", "required": true, "values": ["radial", "bilateral", "axial", "spiral", "orbital"]},
            {"name": "body", "kind": "string", "required": true, "values": ["dome", "bell", "spindle", "sphere", "column", "disc", "cone"]},
            {"name": "length", "kind": "number", "required": true, "range": [0.2, 4.0]},
            {"name": "width", "kind": "number", "required": true, "range": [0.1, 3.0]},
            {"name": "limb", "kind": "string", "required": false, "values": ["hang", "spread", "reach", "spoke", "wing"]},
            {"name": "limbs", "kind": "number", "required": false, "range": [0, 24]},
            {"name": "limb_length", "kind": "number", "required": false, "range": [0.1, 4.0]},
            {"name": "curl", "kind": "number", "required": false, "range": [-2.0, 2.0]},
            {"name": "rings", "kind": "number", "required": false, "range": [0, 6]},
            {"name": "theme", "kind": "string", "required": false, "values": ["bioluminescent", "celestial", "botanical", "fauna", "mechanical", "microscopic", "geological", "ethereal"]}
        ]
    })
}

pub(crate) fn clean(value: f64, lo: f64, hi: f64, fallback: f64) -> f64 {
    if value.is_finite() {
        value.clamp(lo, hi)
    } else {
        fallback
    }
}

fn profile(body: &str, length: f64, width: f64) -> Vec<[f64; 2]> {
    (0..SAMPLES)
        .map(|i| {
            let t = f64::from(i) / f64::from(SAMPLES.saturating_sub(1));
            let y = length * (t - 0.5);
            let (r, y) = match body {
                "dome" => (width * (1.0 - t * t).max(0.0).sqrt(), length * (t - 0.5)),
                "bell" => (width * (1.0 - t.powf(1.6)).max(0.0).sqrt(), y),
                "spindle" => (width * (std::f64::consts::PI * (0.08 + 0.84 * t)).sin(), y),
                "column" => (width * (1.0 - 0.15 * t), y),
                "disc" => (
                    width * (1.0 - t * t).max(0.0).sqrt(),
                    length * 0.2 * (t - 0.5),
                ),
                "cone" => (width * (1.0 - t), y),
                _ => (width * (std::f64::consts::PI * (0.05 + 0.9 * t)).sin(), y),
            };
            [r.max(0.0), y]
        })
        .collect()
}

fn lathe(t: &Traits, length: f64, width: f64) -> Node {
    Node::Lathe {
        profile: profile(&t.body, length, width),
        color: 0,
        weight: 2.0,
    }
}

fn steps_for(count: u32) -> usize {
    let per = 56_u32.checked_div(count.max(1)).unwrap_or(2);
    usize::try_from(per.clamp(2, 5)).unwrap_or(2)
}

fn path_for(curl: f64, hanging: bool) -> PathKind {
    if curl.abs() < 0.05 {
        PathKind::Line
    } else if hanging {
        PathKind::Wave
    } else {
        PathKind::Arc
    }
}

fn radial_limbs(t: &Traits, length: f64, width: f64, limb_length: f64, curl: f64) -> Option<Node> {
    if t.limbs == 0 {
        return None;
    }
    let count = usize::try_from(t.limbs).unwrap_or(1).min(MAX_COUNT);
    let (from_y, dir, rim) = match t.limb.as_str() {
        "hang" => (-length * 0.5, [0.0, -1.0, 0.0], width * 0.8),
        "reach" => (length * 0.5, [0.35, 1.0, 0.0], width * 0.8),
        "spoke" => (0.0, [1.0, 0.0, 0.0], 0.0),
        _ => (0.0, [1.0, -0.15, 0.0], width * 0.8),
    };
    Some(Node::Radial {
        count,
        radius: rim,
        phase: 0.0,
        child: Box::new(Node::Sweep {
            path: path_for(curl, t.limb == "hang"),
            from: [0.0, from_y, 0.0],
            dir,
            length: limb_length,
            bend: curl,
            r0: width * 0.06,
            r1: width * 0.015,
            steps: steps_for(t.limbs),
            color: 2,
            weight: 1.0,
        }),
    })
}

fn bilateral(
    t: &Traits,
    length: f64,
    width: f64,
    limb_length: f64,
    curl: f64,
    nodes: &mut Vec<Node>,
) {
    nodes.push(Node::Rotate {
        axis: Axis::X,
        deg: 90.0,
        child: Box::new(lathe(t, length, width)),
    });
    let pairs = (t.limbs / 2).max(u32::from(t.limbs > 0));
    let (dir, r0, r1) = match t.limb.as_str() {
        "hang" => ([0.3, -1.0, 0.0], width * 0.12, width * 0.05),
        _ => ([1.0, 0.1, -0.3], width * 0.22, width * 0.05),
    };
    let steps = usize::try_from(
        72_u32
            .checked_div(pairs.saturating_mul(2).max(1))
            .unwrap_or(1)
            .clamp(1, 4),
    )
    .unwrap_or(1);
    for k in 0..pairs {
        let spread = if pairs > 1 {
            f64::from(k) / f64::from(pairs.saturating_sub(1)) - 0.5
        } else {
            0.0
        };
        nodes.push(Node::Mirror {
            axis: Axis::X,
            child: Box::new(Node::Sweep {
                path: path_for(curl, false),
                from: [width * 0.5, 0.0, -spread * length * 0.6],
                dir,
                length: limb_length,
                bend: curl,
                r0,
                r1,
                steps,
                color: 3,
                weight: 1.2,
            }),
        });
    }
    nodes.push(Node::Sweep {
        path: PathKind::Line,
        from: [0.0, 0.0, -length * 0.5],
        dir: [0.0, 0.0, -1.0],
        length: limb_length * 0.5,
        bend: 0.0,
        r0: width * 0.2,
        r1: width * 0.03,
        steps: 3,
        color: 2,
        weight: 0.8,
    });
}

fn orbital(t: &Traits, width: f64, nodes: &mut Vec<Node>) {
    nodes.push(Node::Blob {
        shape: Shape::Sphere,
        at: [0.0; 3],
        size: [width * 0.8; 3],
        rot: [0.0; 3],
        color: 0,
        weight: 2.6,
    });
    let rings = t.rings.max(2);
    for i in 0..rings {
        let f = f64::from(i) / f64::from(rings);
        let radius = width * (1.3 + 0.45 * f64::from(i));
        nodes.push(Node::Blob {
            shape: Shape::Torus,
            at: [0.0; 3],
            size: [radius, radius * 0.14, radius],
            rot: [25.0 + f * 40.0, 0.0, -15.0 + f * 55.0],
            color: usize::try_from(i.saturating_add(1)).unwrap_or(1),
            weight: 1.5,
        });
        let theta = f * TAU + 0.5;
        nodes.push(Node::Blob {
            shape: Shape::Sphere,
            at: [
                radius * theta.cos() * 0.85,
                radius * theta.sin() * 0.4,
                radius * (theta * 1.2).sin() * 0.75,
            ],
            size: [width * 0.15; 3],
            rot: [0.0; 3],
            color: usize::try_from(i.saturating_add(3)).unwrap_or(3),
            weight: 0.9,
        });
    }
}

fn spiral(length: f64, width: f64, nodes: &mut Vec<Node>) {
    nodes.push(Node::Radial {
        count: 2,
        radius: 0.0,
        phase: 0.0,
        child: Box::new(Node::Sweep {
            path: PathKind::Spiral,
            from: [0.0, -length * 0.5, 0.0],
            dir: [0.0, 1.0, 0.0],
            length,
            bend: (width / (length * 0.3)).min(2.0),
            r0: width * 0.12,
            r1: width * 0.12,
            steps: 12,
            color: 1,
            weight: 1.5,
        }),
    });
    nodes.push(Node::Blob {
        shape: Shape::Sphere,
        at: [0.0; 3],
        size: [width * 0.25; 3],
        rot: [0.0; 3],
        color: 0,
        weight: 1.2,
    });
}

#[must_use]
pub fn compose(t: &Traits) -> Plan {
    let length = clean(t.length, 0.2, 4.0, 1.5);
    let width = clean(t.width, 0.1, 3.0, 1.0);
    let limb_length = clean(t.limb_length, 0.1, 4.0, 1.0);
    let curl = clean(t.curl, -2.0, 2.0, 0.0);
    let mut traits = t.clone();
    traits.limbs = t.limbs.min(24);
    traits.rings = t.rings.min(6);
    let mut nodes = Vec::new();
    match t.symmetry.as_str() {
        "orbital" => orbital(&traits, width, &mut nodes),
        "spiral" => spiral(length, width, &mut nodes),
        "bilateral" => bilateral(&traits, length, width, limb_length, curl, &mut nodes),
        "axial" => {
            nodes.push(lathe(&traits, length, width));
            for k in 0..traits.rings {
                let f = f64::from(k) / f64::from(traits.rings.max(1)) - 0.5;
                nodes.push(Node::Blob {
                    shape: Shape::Torus,
                    at: [0.0, f * length, 0.0],
                    size: [width * 1.2, width * 0.2, width * 1.2],
                    rot: [0.0; 3],
                    color: usize::try_from(k.saturating_add(1)).unwrap_or(1),
                    weight: 1.2,
                });
            }
        }
        _ => {
            nodes.push(lathe(&traits, length, width));
            nodes.extend(radial_limbs(&traits, length, width, limb_length, curl));
        }
    }
    Plan {
        theme: t.theme.clone(),
        nodes,
    }
}
