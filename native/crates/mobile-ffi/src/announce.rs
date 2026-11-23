use nuxiva_node_core::declare::{Facts, declare};
use serde_json::json;

const AGENT: &str = "ios";
const TEXT_LIMIT: usize = 40;

#[derive(Debug, Clone, PartialEq, Eq, uniffi::Record)]
#[allow(clippy::struct_excessive_bools)]
pub struct DeviceFacts {
    pub version: String,
    pub hostname: String,
    pub microphone: bool,
    pub camera: bool,
    pub cpu_cores: u32,
    pub ram_mb: u64,
}

fn clean(value: &str) -> String {
    value
        .chars()
        .filter(|c| c.is_alphanumeric() || " .,:;@()/+-'".contains(*c))
        .take(TEXT_LIMIT)
        .collect::<String>()
        .trim()
        .to_owned()
}

#[uniffi::export]
#[must_use]
#[allow(clippy::needless_pass_by_value)]
pub fn heartbeat_body(facts: DeviceFacts) -> String {
    let declared = Facts {
        microphone: facts.microphone,
        speaker: true,
        camera: facts.camera,
        sensors: false,
        display: true,
        edge_inference: false,
        cpu_cores: facts.cpu_cores,
        ram_mb: facts.ram_mb,
    };
    json!({
        "agent": AGENT,
        "version": clean(&facts.version),
        "hostname": clean(&facts.hostname),
        "announce": declare(&declared, false),
    })
    .to_string()
}
