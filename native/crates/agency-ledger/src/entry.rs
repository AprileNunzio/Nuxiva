use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Entry {
    pub seq: u64,
    pub at_ms: u64,
    pub kind: String,
    pub payload: Value,
    pub prev: String,
    pub mac: String,
}
