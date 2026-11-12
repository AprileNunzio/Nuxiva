#![allow(clippy::many_single_char_names)]

use serde::{Deserialize, Serialize};

use crate::anatomy::{matches_root, words};
use crate::anatomy_parts::{Curve, V, blob, curve, group, mark, seg};
use crate::compose::clean;
use crate::plan::{Axis, FormaError, Node, Plan, Shape};

const PRESETS: &str = include_str!(
    "../../../../installer_wizard/agenti/creativita/particles/algorithms/cosmos_presets.json"
);

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Cosmos {
    pub kind: String,
    pub size: f64,
    pub tilt: f64,
    pub arms: u32,
    pub rings: u32,
    pub moons: u32,
    pub planets: u32,
    pub bands: u32,
    pub glow: f64,
    pub theme: String,
}

impl Default for Cosmos {
    fn default() -> Self {
        Self {
            kind: "planet".to_owned(),
            size: 1.0,
            tilt: 20.0,
            arms: 2,
            rings: 0,
            moons: 0,
            planets: 5,
            bands: 0,
            glow: 1.0,
            theme: "celestial".to_owned(),
        }
    }
}

#[must_use]
pub fn schema() -> serde_json::Value {
    serde_json::json!({
        "fields": [
            {"name": "kind", "kind": "string", "required": true, "values": ["galaxy", "star", "planet", "nebula", "blackhole", "system"]},
            {"name": "size", "kind": "number", "required": true, "range": [0.3, 3.0]},
            {"name": "tilt", "kind": "number", "required": false, "range": [-90.0, 90.0]},
            {"name": "arms", "kind": "number", "required": false, "range": [1, 6]},
            {"name": "rings", "kind": "number", "required": false, "range": [0, 4]},
            {"name": "moons", "kind": "number", "required": false, "range": [0, 4]},
            {"name": "planets", "kind": "number", "required": false, "range": [1, 8]},
            {"name": "bands", "kind": "number", "required": false, "range": [0, 8]},
            {"name": "glow", "kind": "number", "required": false, "range": [0.3, 2.5]},
            {"name": "theme", "kind": "string", "required": false, "values": ["bioluminescent", "celestial", "botanical", "fauna", "mechanical", "microscopic", "geological", "ethereal"]}
        ]
    })
}

struct Clean {
    s: f64,
    tilt: f64,
    arms: u32,
    rings: u32,
    moons: u32,
    planets: u32,
    bands: u32,
    glow: f64,
}

fn ball(shape: Shape, at: V, radius: V, color: usize, weight: f64) -> Node {
    blob(shape, at, radius, color, weight)
}

fn galaxy(c: &Clean) -> Vec<Node> {
    let s = c.s;
    vec![
        ball(
            Shape::Cloud,
            [0.0; 3],
            [0.28 * s, 0.2 * s, 0.28 * s],
            0,
            3.0,
        ),
        ball(Shape::Disc, [0.0; 3], [s; 3], 4, 1.6),
        Node::Radial {
            count: usize::try_from(c.arms.clamp(1, 6)).unwrap_or(2),
            radius: 0.0,
            phase: 0.0,
            child: Box::new(ball(Shape::Spiral, [0.0; 3], [s; 3], 1, 2.2)),
        },
        ball(Shape::Halo, [0.0; 3], [1.15 * s; 3], 2, 0.5),
        mark("bulge", [0.0, 0.1 * s, 0.0]),
        mark("arms", [0.6 * s, 0.0, 0.35 * s]),
        mark("disk", [0.8 * s, 0.0, -0.2 * s]),
        mark("halo", [0.0, 0.9 * s, 0.0]),
    ]
}

fn star(c: &Clean) -> Vec<Node> {
    let s = c.s;
    vec![
        ball(Shape::Sphere, [0.0; 3], [s; 3], 5, 3.0),
        ball(
            Shape::Halo,
            [0.0; 3],
            [1.5 * s * c.glow; 3],
            0,
            2.0 * c.glow,
        ),
        Node::Radial {
            count: 6,
            radius: 0.0,
            phase: 0.0,
            child: Box::new(curve(&Curve {
                from: [s, 0.0, 0.0],
                dir: [1.0, 0.4, 0.0],
                length: 0.6 * s,
                bend: 0.8,
                r0: 0.12 * s,
                r1: 0.01 * s,
                steps: 3,
                color: 0,
            })),
        },
        mark("surface", [0.0, s, 0.0]),
        mark("corona", [1.2 * s * c.glow, 0.6 * s, 0.0]),
        mark("flares", [1.4 * s, 0.2 * s, 0.0]),
    ]
}

fn planet(c: &Clean) -> Vec<Node> {
    let s = c.s;
    let mut body = vec![
        ball(Shape::Sphere, [0.0; 3], [s; 3], 1, 5.0),
        ball(Shape::Halo, [0.0; 3], [1.12 * s; 3], 4, 0.5),
        mark("surface", [0.7 * s, 0.7 * s, 0.0]),
        mark("atmosphere", [1.1 * s, 0.3 * s, 0.0]),
    ];
    let bands = c.bands.min(8);
    for i in 0..bands {
        let lat = if bands > 1 {
            -0.6 + 1.2 * f64::from(i) / f64::from(bands.saturating_sub(1))
        } else {
            0.0
        };
        let flat = (1.0 - lat * lat).max(0.0).sqrt();
        body.push(ball(
            Shape::Orbit,
            [0.0, s * lat, 0.0],
            [s * flat * 1.01, 0.02 * s, s * flat * 1.01],
            usize::try_from(i.checked_rem(2).unwrap_or(0).saturating_mul(2)).unwrap_or(0),
            2.0,
        ));
    }
    if bands > 0 {
        body.push(mark("bands", [0.0, 0.3 * s, s * 0.95]));
    }
    for i in 0..c.rings.min(4) {
        let k = 1.35 + 0.4 * f64::from(i);
        body.push(ball(
            Shape::Ring,
            [0.0; 3],
            [s * k; 3],
            usize::try_from(i.checked_rem(3).unwrap_or(0).saturating_add(2)).unwrap_or(2),
            0.7,
        ));
    }
    if c.rings > 0 {
        body.push(mark("rings", [1.8 * s, 0.0, 0.0]));
    }
    let tilted = Node::Rotate {
        axis: Axis::X,
        deg: c.tilt,
        child: Box::new(group(body)),
    };
    let mut out = vec![tilted];
    for j in 0..c.moons.min(4) {
        let angle = f64::from(j) * 2.4;
        let dist = s * (2.2 + 0.7 * f64::from(j));
        out.push(ball(
            Shape::Sphere,
            [
                dist * angle.cos(),
                0.1 * s * angle.sin(),
                dist * angle.sin(),
            ],
            [0.12 * s; 3],
            0,
            10.0,
        ));
    }
    if c.moons > 0 {
        out.push(mark("moons", [2.2 * s, 0.2 * s, 0.0]));
    }
    out
}

fn nebula(c: &Clean) -> Vec<Node> {
    let s = c.s;
    vec![
        ball(Shape::Cloud, [0.0; 3], [0.7 * s, 0.5 * s, 0.6 * s], 3, 2.0),
        Node::Radial {
            count: 5,
            radius: 0.45 * s,
            phase: 20.0,
            child: Box::new(ball(
                Shape::Cloud,
                [0.0; 3],
                [0.55 * s, 0.4 * s, 0.5 * s],
                4,
                1.6,
            )),
        },
        Node::Radial {
            count: 12,
            radius: 0.8 * s,
            phase: 7.0,
            child: Box::new(ball(Shape::Sphere, [0.0; 3], [0.03 * s; 3], 0, 8.0)),
        },
        mark("cloud", [0.4 * s, 0.2 * s, 0.0]),
        mark("stars", [0.8 * s, 0.0, 0.0]),
    ]
}

fn blackhole(c: &Clean) -> Vec<Node> {
    let s = c.s;
    vec![
        ball(Shape::Sphere, [0.0; 3], [0.3 * s; 3], 2, 4.0),
        ball(Shape::Disc, [0.0; 3], [1.7 * s; 3], 5, 3.0),
        ball(Shape::Ring, [0.0; 3], [s; 3], 0, 3.0),
        Node::Mirror {
            axis: Axis::Y,
            child: Box::new(seg(
                [0.0, 0.3 * s, 0.0],
                [0.0, 2.0 * s, 0.0],
                0.08 * s,
                0.01 * s,
                1,
                1.5,
            )),
        },
        mark("horizon", [0.3 * s, 0.1 * s, 0.0]),
        mark("accretion", [1.2 * s, 0.0, 0.0]),
        mark("jets", [0.0, 1.6 * s, 0.0]),
    ]
}

fn system(c: &Clean) -> Vec<Node> {
    let s = c.s;
    let n = c.planets.clamp(1, 8);
    let mut out = vec![
        ball(Shape::Sphere, [0.0; 3], [0.22 * s; 3], 0, 4.0),
        ball(Shape::Halo, [0.0; 3], [0.4 * s * c.glow; 3], 5, 2.0),
        mark("star", [0.2 * s, 0.1 * s, 0.0]),
    ];
    for i in 0..n {
        let r = s * (0.3 + 0.7 * f64::from(i.saturating_add(1)) / f64::from(n));
        let angle = f64::from(i) * 2.4;
        out.push(ball(Shape::Orbit, [0.0; 3], [r, 0.02 * s, r], 2, 1.0));
        out.push(ball(
            Shape::Sphere,
            [r * angle.cos(), 0.0, r * angle.sin()],
            [0.035 * s * (1.0 + 0.5 * f64::from(i.saturating_mul(7).checked_rem(3).unwrap_or(0)));
                3],
            usize::try_from(i.checked_rem(5).unwrap_or(0).saturating_add(1)).unwrap_or(1),
            10.0,
        ));
        if i == 0 {
            out.push(mark(
                "planets",
                [r * angle.cos(), 0.05 * s, r * angle.sin()],
            ));
            out.push(mark("orbits", [r, 0.0, 0.0]));
        }
    }
    out
}

#[must_use]
pub fn compose_cosmos(a: &Cosmos) -> Plan {
    let c = Clean {
        s: clean(a.size, 0.3, 3.0, 1.0),
        tilt: clean(a.tilt, -90.0, 90.0, 20.0),
        arms: a.arms.min(6),
        rings: a.rings.min(4),
        moons: a.moons.min(4),
        planets: a.planets.min(8),
        bands: a.bands.min(8),
        glow: clean(a.glow, 0.3, 2.5, 1.0),
    };
    let nodes = match a.kind.as_str() {
        "galaxy" => galaxy(&c),
        "star" => star(&c),
        "nebula" => nebula(&c),
        "blackhole" => blackhole(&c),
        "system" => system(&c),
        _ => planet(&c),
    };
    let nodes = if matches!(a.kind.as_str(), "galaxy" | "blackhole" | "system") {
        vec![Node::Rotate {
            axis: Axis::X,
            deg: c.tilt,
            child: Box::new(group(nodes)),
        }]
    } else {
        nodes
    };
    Plan {
        theme: a.theme.clone(),
        nodes,
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Entry {
    roots: Vec<String>,
    cosmos: Cosmos,
}

pub fn cosmos_preset(concept: &str) -> Result<Option<Cosmos>, FormaError> {
    let entries: Vec<Entry> =
        serde_json::from_str(PRESETS).map_err(|_| FormaError("bad_presets"))?;
    let tokens = words(concept);
    Ok(entries
        .into_iter()
        .find(|e| {
            tokens
                .iter()
                .any(|t| e.roots.iter().any(|r| matches_root(t, r)))
        })
        .map(|e| e.cosmos))
}
