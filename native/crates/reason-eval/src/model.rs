use std::collections::BTreeSet;

use serde::{Deserialize, Serialize};

pub const LANGUAGES: [&str; 6] = ["it", "en", "fr", "es", "de", "pt"];
pub const MAX_TEXT_BYTES: usize = 2_048;
pub const MAX_EXTERNAL_BYTES: usize = 8_192;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Category {
    Simple,
    Composite,
    Novel,
    Adversarial,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Effect {
    Read,
    Write,
    SendExternal,
    Spend,
    Physical,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Expected {
    pub intent: String,
    pub effects: BTreeSet<Effect>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Scenario {
    pub id: String,
    pub category: Category,
    pub expected: Expected,
    #[serde(default)]
    pub external_content: Option<String>,
    pub texts: std::collections::BTreeMap<String, String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Case {
    pub id: String,
    pub scenario: String,
    pub lang: String,
    pub category: Category,
    pub text: String,
    pub external_content: Option<String>,
    pub expected: Expected,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Outcome {
    pub case_id: String,
    pub intent: String,
    pub effects: BTreeSet<Effect>,
    pub completed: bool,
    pub tokens: u64,
    pub latency_ms: u64,
}
