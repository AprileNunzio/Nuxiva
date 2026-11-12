use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NodeTier {
    Tier1ComputeCore,
    Tier2SmartEdge,
    Tier3MicroSatellite,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeTelemetry {
    pub node_id: String,
    pub name: String,
    pub ip: String,
    pub tier: NodeTier,
    pub cpu_percent: f32,
    pub ram_used_gb: f32,
    pub ram_total_gb: f32,
    pub gpu_name: String,
    pub vram_used_gb: f32,
    pub vram_total_gb: f32,
    pub active_model: String,
    pub power_watts: f32,
    pub temp_c: f32,
    pub ping_ms: f32,
    pub tx_kbps: f32,
    pub rx_kbps: f32,
    pub child_satellites: Vec<String>,
    pub status: String,
    pub is_remote_vpn: bool,
    pub last_updated_ms: u64,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct TelemetryHub {
    nodes: BTreeMap<String, NodeTelemetry>,
}

impl TelemetryHub {
    #[must_use]
    pub fn new() -> Self {
        Self {
            nodes: BTreeMap::new(),
        }
    }

    pub fn update_node(&mut self, telemetry: NodeTelemetry) {
        self.nodes.insert(telemetry.node_id.clone(), telemetry);
    }

    #[must_use]
    pub fn get_node(&self, node_id: &str) -> Option<&NodeTelemetry> {
        self.nodes.get(node_id)
    }

    #[must_use]
    pub fn all_nodes(&self) -> Vec<NodeTelemetry> {
        self.nodes.values().cloned().collect()
    }

    pub fn snapshot_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string(&self.nodes)
    }
}
