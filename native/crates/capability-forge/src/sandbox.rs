use std::collections::{BTreeMap, BTreeSet};

use capability_registry::Effect;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    Wasm,
    Script,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Artifact {
    pub kind: Kind,
    pub digest: String,
    pub size: usize,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Expect {
    NonEmpty,
    Contains(String),
    Equals(String),
}

impl Expect {
    #[must_use]
    pub fn holds(&self, output: &str) -> bool {
        match self {
            Self::NonEmpty => !output.trim().is_empty(),
            Self::Contains(part) => output.contains(part.as_str()),
            Self::Equals(whole) => output == whole,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Probe {
    pub input: BTreeMap<String, String>,
    pub expect: Expect,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Observation {
    pub output: String,
    pub effects: BTreeSet<Effect>,
    pub millis: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SandboxError {
    Crashed,
    Denied,
}

pub trait Sandbox {
    fn run(
        &mut self,
        artifact: &Artifact,
        input: &BTreeMap<String, String>,
    ) -> Result<Observation, SandboxError>;
}
