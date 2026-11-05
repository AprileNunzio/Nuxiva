use crate::grid::Slot;
use nuxiva_display_domain::AudienceKind;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Mode {
    Conversation,
    Project,
    #[default]
    Ambient,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Screen {
    pub id: i32,
    #[serde(default = "wide")]
    pub aspect: f32,
    #[serde(default)]
    pub role: Option<String>,
    #[serde(default = "yes")]
    pub webgl2: bool,
    #[serde(default = "budget")]
    pub budget: f32,
}

const fn wide() -> f32 {
    16.0 / 9.0
}

const fn yes() -> bool {
    true
}

const fn budget() -> f32 {
    12.0
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Context {
    pub audience: AudienceKind,
    #[serde(default)]
    pub present: Vec<String>,
    #[serde(default)]
    pub alone: bool,
    #[serde(default)]
    pub mode: Mode,
    #[serde(default)]
    pub guest_public: bool,
    #[serde(default)]
    pub trust_guests: bool,
    #[serde(default)]
    pub cap: Option<u8>,
}

#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Previous {
    #[serde(default)]
    pub shown: BTreeMap<String, (Slot, u64)>,
}
