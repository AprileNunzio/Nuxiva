use crate::error::{NodeError, NodeResult};
use crate::scope;
use serde_json::Value;

pub const MAX_ANNOUNCE: usize = 16 * 1024;
pub const MAX_CAPABILITIES: usize = 64;
const MAX_CORES: u32 = 4096;
const MAX_RAM_MB: u64 = 16 * 1024 * 1024;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Hardware {
    pub cpu_cores: u32,
    pub ram_mb: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct Announce {
    pub scopes: Vec<String>,
    pub rejected: Vec<String>,
    pub hardware: Hardware,
    pub full_host: bool,
}

fn counter(value: Option<&Value>, ceiling: u64) -> NodeResult<u64> {
    match value {
        None => Ok(0),
        Some(v) => v.as_u64().map(|n| n.min(ceiling)).ok_or(NodeError::Payload),
    }
}

pub fn parse(json: &str) -> NodeResult<Announce> {
    if json.len() > MAX_ANNOUNCE {
        return Err(NodeError::TooLarge);
    }
    let value: Value = serde_json::from_str(json).map_err(|_| NodeError::Payload)?;
    let object = value.as_object().ok_or(NodeError::Payload)?;
    let caps: &[Value] = match object.get("capabilities") {
        None => &[],
        Some(Value::Array(items)) => items,
        Some(_) => return Err(NodeError::Payload),
    };
    let hardware = match object.get("hardware") {
        None => None,
        Some(Value::Object(map)) => Some(map),
        Some(_) => return Err(NodeError::Payload),
    };
    if caps.len() > MAX_CAPABILITIES {
        return Err(NodeError::TooMany);
    }
    let mut scopes = Vec::new();
    let mut rejected = Vec::new();
    for item in caps {
        let name = item
            .as_object()
            .and_then(|map| map.get("scope"))
            .and_then(Value::as_str)
            .ok_or(NodeError::Payload)?;
        if scope::valid(name) && !scope::forbidden(name) {
            scopes.push(name.to_owned());
        } else {
            rejected.push(
                name.chars()
                    .filter(|c| !c.is_control())
                    .take(scope::MAX_SCOPE)
                    .collect(),
            );
        }
    }
    scopes.sort();
    scopes.dedup();
    rejected.sort();
    rejected.dedup();
    let cores = counter(
        hardware.and_then(|h| h.get("cpu_cores")),
        u64::from(MAX_CORES),
    )?;
    let ram_mb = counter(hardware.and_then(|h| h.get("ram_mb")), MAX_RAM_MB)?;
    let hardware = Hardware {
        cpu_cores: u32::try_from(cores).unwrap_or(0),
        ram_mb,
    };
    let full_host = scopes.iter().any(|s| s == "node.host_full");
    Ok(Announce {
        scopes,
        rejected,
        hardware,
        full_host,
    })
}
