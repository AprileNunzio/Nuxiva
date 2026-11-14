use serde_json::{Value, json};

use crate::scope::SECOND_SERVER_EXTRA;

const HOST_SCOPES: &[&str] = &[
    "node.host_full",
    "compute.lease",
    "agents.run",
    "mcp.serve",
    "storage.replica",
    "inference.host",
];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
#[allow(clippy::struct_excessive_bools)]
pub struct Facts {
    pub microphone: bool,
    pub speaker: bool,
    pub camera: bool,
    pub sensors: bool,
    pub display: bool,
    pub edge_inference: bool,
    pub cpu_cores: u32,
    pub ram_mb: u64,
}

#[must_use]
pub fn scopes(facts: &Facts, host_full: bool) -> Vec<String> {
    let mut out: Vec<&str> = vec!["telemetry.report"];
    for (present, scope) in [
        (facts.microphone, "audio.capture"),
        (facts.speaker, "audio.play"),
        (facts.camera, "camera.stream"),
        (facts.sensors, "sensor.read"),
        (facts.display, "display.render"),
        (facts.edge_inference, "inference.edge"),
    ] {
        if present {
            out.push(scope);
        }
    }
    if host_full {
        out.extend(
            HOST_SCOPES
                .iter()
                .filter(|s| SECOND_SERVER_EXTRA.contains(s)),
        );
    }
    out.sort_unstable();
    out.dedup();
    out.into_iter().map(str::to_owned).collect()
}

#[must_use]
pub fn declare(facts: &Facts, host_full: bool) -> Value {
    let capabilities: Vec<Value> = scopes(facts, host_full)
        .into_iter()
        .map(|scope| json!({ "scope": scope }))
        .collect();
    json!({
        "capabilities": capabilities,
        "hardware": {"cpu_cores": facts.cpu_cores, "ram_mb": facts.ram_mb},
    })
}
