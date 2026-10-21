use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum StreamKind {
    AudioPcm,
    VideoRtsp,
    WebRtc,
    SensorTelemetry,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DirectStreamBinding {
    pub satellite_id: String,
    pub satellite_ip: String,
    pub parent_node_id: String,
    pub parent_ip: String,
    pub stream_kind: StreamKind,
    pub active: bool,
    pub bytes_transferred: u64,
}

impl DirectStreamBinding {
    #[must_use]
    pub const fn new(
        satellite_id: String,
        satellite_ip: String,
        parent_node_id: String,
        parent_ip: String,
        stream_kind: StreamKind,
    ) -> Self {
        Self {
            satellite_id,
            satellite_ip,
            parent_node_id,
            parent_ip,
            stream_kind,
            active: true,
            bytes_transferred: 0,
        }
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct P2PStreamManager {
    bindings: BTreeMap<String, DirectStreamBinding>,
}

impl P2PStreamManager {
    #[must_use]
    pub fn new() -> Self {
        Self {
            bindings: BTreeMap::new(),
        }
    }

    pub fn register_binding(
        &mut self,
        satellite_id: impl Into<String>,
        satellite_ip: impl Into<String>,
        parent_node_id: impl Into<String>,
        parent_ip: impl Into<String>,
        kind: StreamKind,
    ) {
        let sat_id = satellite_id.into();
        let binding = DirectStreamBinding::new(
            sat_id.clone(),
            satellite_ip.into(),
            parent_node_id.into(),
            parent_ip.into(),
            kind,
        );
        self.bindings.insert(sat_id, binding);
    }

    #[must_use]
    pub fn get_binding(&self, satellite_id: &str) -> Option<&DirectStreamBinding> {
        self.bindings.get(satellite_id)
    }

    #[must_use]
    pub fn resolve_direct_target(&self, satellite_id: &str) -> Option<&str> {
        let b = self.bindings.get(satellite_id)?;
        if b.active { Some(&b.parent_ip) } else { None }
    }

    pub fn record_transfer(&mut self, satellite_id: &str, bytes: u64) -> bool {
        if let Some(b) = self.bindings.get_mut(satellite_id) {
            b.bytes_transferred = b.bytes_transferred.saturating_add(bytes);
            true
        } else {
            false
        }
    }

    pub fn set_active(&mut self, satellite_id: &str, active: bool) -> bool {
        if let Some(b) = self.bindings.get_mut(satellite_id) {
            b.active = active;
            true
        } else {
            false
        }
    }

    #[must_use]
    pub fn active_bindings(&self) -> Vec<DirectStreamBinding> {
        self.bindings
            .values()
            .filter(|b| b.active)
            .cloned()
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_direct_stream_routing() {
        let mut manager = P2PStreamManager::new();
        manager.register_binding(
            "rpi-cam-1",
            "192.168.1.50",
            "pc-i9-core",
            "192.168.1.10",
            StreamKind::VideoRtsp,
        );

        let target_ip = manager.resolve_direct_target("rpi-cam-1");
        assert_eq!(target_ip, Some("192.168.1.10"));

        assert!(manager.record_transfer("rpi-cam-1", 1024));
        let binding = manager.get_binding("rpi-cam-1");
        assert_eq!(binding.map(|b| b.bytes_transferred), Some(1024));
    }
}
