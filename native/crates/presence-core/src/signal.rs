use serde::{Deserialize, Serialize};

pub const MAX_FACES: usize = 32;
pub const MAX_VOICES: usize = 64;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Vision {
    Ok,
    #[default]
    Offline,
    Disabled,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Liveness {
    Live,
    #[default]
    Unknown,
    Spoof,
}

#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Face {
    pub person: Option<String>,
    pub authorized: bool,
    pub confidence: f32,
    pub liveness: Liveness,
    pub near: bool,
}

#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Voice {
    pub person: Option<String>,
    pub authorized: bool,
    pub score: f32,
    pub at_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct Signals {
    pub vision: Vision,
    pub faces: Vec<Face>,
    pub voices: Vec<Voice>,
}
