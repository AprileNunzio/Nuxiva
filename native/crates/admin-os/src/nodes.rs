use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum HardwareTarget {
    Pc,
    Raspberry,
    Esp32,
    Android,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum NodeTier {
    Compute,
    Satellite,
    Micro,
    Mobile,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum NodeStatus {
    Online,
    Offline,
    Pairing,
    Degraded,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct NodeInfo {
    pub id: String,
    pub name: String,
    pub target: HardwareTarget,
    pub tier: NodeTier,
    pub ip: Option<String>,
    pub mac: Option<String>,
    pub parent_id: Option<String>,
    pub is_local: bool,
    pub status: NodeStatus,
    pub registered_at_secs: u64,
    pub last_heartbeat_secs: u64,
}

impl NodeInfo {
    #[must_use]
    pub fn new(
        id: impl Into<String>,
        name: impl Into<String>,
        target: HardwareTarget,
        tier: NodeTier,
        registered_at: u64,
    ) -> Self {
        Self {
            id: id.into(),
            name: name.into(),
            target,
            tier,
            ip: None,
            mac: None,
            parent_id: None,
            is_local: false,
            status: NodeStatus::Pairing,
            registered_at_secs: registered_at,
            last_heartbeat_secs: registered_at,
        }
    }

    #[must_use]
    pub fn with_ip(mut self, ip: impl Into<String>) -> Self {
        self.ip = Some(ip.into());
        self
    }

    #[must_use]
    pub fn with_parent(mut self, parent: impl Into<String>) -> Self {
        self.parent_id = Some(parent.into());
        self
    }

    pub fn set_online(&mut self, is_online: bool, now: u64) {
        self.status = if is_online {
            NodeStatus::Online
        } else {
            NodeStatus::Offline
        };
        self.last_heartbeat_secs = now;
    }

    #[must_use]
    pub fn is_active(&self, now: u64, stale_timeout_secs: u64) -> bool {
        self.status == NodeStatus::Online
            && now.saturating_sub(self.last_heartbeat_secs) <= stale_timeout_secs
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
pub struct NodesSummary {
    pub total: usize,
    pub online: usize,
    pub compute: usize,
    pub satellite: usize,
    pub micro: usize,
    pub mobile: usize,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct NodeManager {
    nodes: Vec<NodeInfo>,
}

impl NodeManager {
    #[must_use]
    pub fn new() -> Self {
        Self { nodes: Vec::new() }
    }

    pub fn register_node(&mut self, node: NodeInfo) {
        if let Some(existing) = self.nodes.iter_mut().find(|n| n.id == node.id) {
            *existing = node;
        } else {
            self.nodes.push(node);
        }
    }

    pub fn deregister_node(&mut self, id: &str) -> bool {
        if let Some(pos) = self.nodes.iter().position(|n| n.id == id) {
            self.nodes.remove(pos);
            true
        } else {
            false
        }
    }

    #[must_use]
    pub fn node(&self, id: &str) -> Option<&NodeInfo> {
        self.nodes.iter().find(|n| n.id == id)
    }

    #[must_use]
    pub fn nodes(&self) -> &[NodeInfo] {
        &self.nodes
    }

    pub fn update_heartbeat(&mut self, id: &str, now: u64) -> bool {
        if let Some(node) = self.nodes.iter_mut().find(|n| n.id == id) {
            node.last_heartbeat_secs = now;
            node.status = NodeStatus::Online;
            true
        } else {
            false
        }
    }

    #[must_use]
    pub fn summary(&self, now: u64, stale_timeout_secs: u64) -> NodesSummary {
        let mut sum = NodesSummary {
            total: self.nodes.len(),
            ..Default::default()
        };

        for n in &self.nodes {
            if n.is_active(now, stale_timeout_secs) {
                sum.online = sum.online.saturating_add(1);
            }
            match n.tier {
                NodeTier::Compute => sum.compute = sum.compute.saturating_add(1),
                NodeTier::Satellite => sum.satellite = sum.satellite.saturating_add(1),
                NodeTier::Micro => sum.micro = sum.micro.saturating_add(1),
                NodeTier::Mobile => sum.mobile = sum.mobile.saturating_add(1),
            }
        }

        sum
    }

    #[must_use]
    pub fn validate_pairing_code(code: &str) -> bool {
        let trimmed = code.trim();
        if trimmed.len() != 6 && trimmed.len() != 8 {
            return false;
        }
        trimmed
            .chars()
            .all(|c| c.is_ascii_digit() || c.is_ascii_uppercase())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_node_lifecycle_and_heartbeat() {
        let mut mgr = NodeManager::new();
        let now = 1000u64;

        let mut node = NodeInfo::new(
            "node-1",
            "Living Room Satellite",
            HardwareTarget::Raspberry,
            NodeTier::Satellite,
            now,
        )
        .with_ip("192.168.1.42")
        .with_parent("virtual_core");

        node.set_online(true, now);
        mgr.register_node(node);

        assert_eq!(mgr.nodes().len(), 1);
        let retrieved = mgr.node("node-1");
        assert!(retrieved.is_some());
        assert_eq!(
            retrieved.map(|n| n.name.as_str()),
            Some("Living Room Satellite")
        );

        let sum = mgr.summary(now + 10, 30);
        assert_eq!(sum.total, 1);
        assert_eq!(sum.online, 1);
        assert_eq!(sum.satellite, 1);
        assert_eq!(sum.compute, 0);

        let stale_sum = mgr.summary(now + 40, 30);
        assert_eq!(stale_sum.online, 0);

        assert!(mgr.update_heartbeat("node-1", now + 40));
        let refreshed_sum = mgr.summary(now + 40, 30);
        assert_eq!(refreshed_sum.online, 1);

        assert!(mgr.deregister_node("node-1"));
        assert_eq!(mgr.nodes().len(), 0);
    }

    #[test]
    fn test_pairing_code_validation() {
        assert!(NodeManager::validate_pairing_code("123456"));
        assert!(NodeManager::validate_pairing_code("AB12CD"));
        assert!(NodeManager::validate_pairing_code("ABCDEF12"));
        assert!(!NodeManager::validate_pairing_code("12345"));
        assert!(!NodeManager::validate_pairing_code("123456789"));
        assert!(!NodeManager::validate_pairing_code("ab12cd"));
        assert!(!NodeManager::validate_pairing_code("12 456"));
    }
}
