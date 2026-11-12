use serde::{Deserialize, Serialize};

use crate::anatomy_plans::{biped, bird, fish, insect, quadruped, serpent};
use crate::compose::clean;
use crate::plan::{FormaError, Plan};

const PRESETS: &str = include_str!(
    "../../../../installer_wizard/agenti/creativita/particles/algorithms/anatomy_presets.json"
);
const MAX_CONCEPT: usize = 256;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Anatomy {
    pub plan: String,
    pub size: f64,
    pub build: f64,
    pub neck: f64,
    pub head: f64,
    pub snout: f64,
    pub ears: String,
    pub ear_size: f64,
    pub horns: f64,
    pub tail: f64,
    pub tail_curl: f64,
    pub legs: f64,
    pub leg_thick: f64,
    pub arms: f64,
    pub wings: f64,
    pub pairs: u32,
    pub theme: String,
}

impl Default for Anatomy {
    fn default() -> Self {
        Self {
            plan: "quadruped".to_owned(),
            size: 1.6,
            build: 1.0,
            neck: 0.5,
            head: 1.0,
            snout: 0.5,
            ears: "point".to_owned(),
            ear_size: 1.0,
            horns: 0.0,
            tail: 1.0,
            tail_curl: 0.4,
            legs: 1.0,
            leg_thick: 1.0,
            arms: 1.0,
            wings: 0.0,
            pairs: 3,
            theme: "fauna".to_owned(),
        }
    }
}

pub(crate) struct Cleaned {
    pub(crate) size: f64,
    pub(crate) build: f64,
    pub(crate) neck: f64,
    pub(crate) head: f64,
    pub(crate) snout: f64,
    pub(crate) ears: String,
    pub(crate) ear_size: f64,
    pub(crate) horns: f64,
    pub(crate) tail: f64,
    pub(crate) tail_curl: f64,
    pub(crate) legs: f64,
    pub(crate) leg_thick: f64,
    pub(crate) arms: f64,
    pub(crate) wings: f64,
    pub(crate) pairs: u32,
}

impl Cleaned {
    fn new(a: &Anatomy) -> Self {
        Self {
            size: clean(a.size, 0.4, 4.0, 1.6),
            build: clean(a.build, 0.3, 2.0, 1.0),
            neck: clean(a.neck, 0.0, 2.5, 0.5),
            head: clean(a.head, 0.2, 2.0, 1.0),
            snout: clean(a.snout, 0.0, 2.5, 0.5),
            ears: a.ears.clone(),
            ear_size: clean(a.ear_size, 0.2, 2.5, 1.0),
            horns: clean(a.horns, 0.0, 2.5, 0.0),
            tail: clean(a.tail, 0.0, 3.0, 1.0),
            tail_curl: clean(a.tail_curl, -2.0, 2.0, 0.4),
            legs: clean(a.legs, 0.2, 2.5, 1.0),
            leg_thick: clean(a.leg_thick, 0.3, 2.5, 1.0),
            arms: clean(a.arms, 0.2, 2.5, 1.0),
            wings: clean(a.wings, 0.0, 3.0, 0.0),
            pairs: a.pairs.min(6),
        }
    }
}

#[must_use]
pub fn schema() -> serde_json::Value {
    serde_json::json!({
        "fields": [
            {"name": "plan", "kind": "string", "required": true, "values": ["quadruped", "biped", "bird", "fish", "insect", "serpent"]},
            {"name": "size", "kind": "number", "required": true, "range": [0.4, 4.0]},
            {"name": "build", "kind": "number", "required": false, "range": [0.3, 2.0]},
            {"name": "neck", "kind": "number", "required": false, "range": [0.0, 2.5]},
            {"name": "head", "kind": "number", "required": false, "range": [0.2, 2.0]},
            {"name": "snout", "kind": "number", "required": false, "range": [0.0, 2.5]},
            {"name": "ears", "kind": "string", "required": false, "values": ["none", "point", "round", "floppy", "long"]},
            {"name": "ear_size", "kind": "number", "required": false, "range": [0.2, 2.5]},
            {"name": "horns", "kind": "number", "required": false, "range": [0.0, 2.5]},
            {"name": "tail", "kind": "number", "required": false, "range": [0.0, 3.0]},
            {"name": "tail_curl", "kind": "number", "required": false, "range": [-2.0, 2.0]},
            {"name": "legs", "kind": "number", "required": false, "range": [0.2, 2.5]},
            {"name": "leg_thick", "kind": "number", "required": false, "range": [0.3, 2.5]},
            {"name": "arms", "kind": "number", "required": false, "range": [0.2, 2.5]},
            {"name": "wings", "kind": "number", "required": false, "range": [0.0, 3.0]},
            {"name": "pairs", "kind": "number", "required": false, "range": [1, 6]},
            {"name": "theme", "kind": "string", "required": false, "values": ["bioluminescent", "celestial", "botanical", "fauna", "mechanical", "microscopic", "geological", "ethereal"]}
        ]
    })
}

#[must_use]
pub fn compose_anatomy(a: &Anatomy) -> Plan {
    let p = Cleaned::new(a);
    let nodes = match a.plan.as_str() {
        "biped" => biped(&p),
        "bird" => bird(&p),
        "fish" => fish(&p),
        "insect" => insect(&p),
        "serpent" => serpent(&p),
        _ => quadruped(&p),
    };
    Plan {
        theme: a.theme.clone(),
        nodes,
    }
}

fn words(concept: &str) -> Vec<String> {
    concept
        .chars()
        .take(MAX_CONCEPT)
        .map(|c| {
            if c.is_alphanumeric() {
                c.to_lowercase().next().unwrap_or(' ')
            } else {
                ' '
            }
        })
        .collect::<String>()
        .split_whitespace()
        .map(str::to_owned)
        .collect()
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Entry {
    roots: Vec<String>,
    anatomy: Anatomy,
}

fn matches_root(token: &str, root: &str) -> bool {
    root.strip_suffix('*').map_or(token == root, |stem| {
        token.len() >= 3 && token.starts_with(stem)
    })
}

pub fn preset(concept: &str) -> Result<Option<Anatomy>, FormaError> {
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
        .map(|e| e.anatomy))
}
