use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::str::FromStr;

pub const MAX_MESH_PEERS: usize = 10_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NodeStatus {
    Alive,
    Suspect,
    Dead,
    Left,
}

impl NodeStatus {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Alive => "alive",
            Self::Suspect => "suspect",
            Self::Dead => "dead",
            Self::Left => "left",
        }
    }
}

impl FromStr for NodeStatus {
    type Err = std::convert::Infallible;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let val = match s {
            "suspect" => Self::Suspect,
            "dead" => Self::Dead,
            "left" => Self::Left,
            _ => Self::Alive,
        };
        Ok(val)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PeerDescriptor {
    pub id: String,
    pub endpoint: String,
    pub status: NodeStatus,
    pub heartbeat: u64,
    pub incarnation: u64,
    pub last_seen_epoch_ms: u64,
    pub metadata_json: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GossipMesh {
    local_id: String,
    local_endpoint: String,
    local_heartbeat: u64,
    local_incarnation: u64,
    peers: BTreeMap<String, PeerDescriptor>,
    rr_cursor: usize,
}

impl GossipMesh {
    #[must_use]
    pub fn new(local_id: &str, local_endpoint: &str) -> Self {
        Self {
            local_id: local_id.to_string(),
            local_endpoint: local_endpoint.to_string(),
            local_heartbeat: 0,
            local_incarnation: 1,
            peers: BTreeMap::new(),
            rr_cursor: 0,
        }
    }

    pub fn heartbeat(&mut self, now_ms: u64) {
        self.local_heartbeat = self.local_heartbeat.saturating_add(1);
        if let Some(entry) = self.peers.get_mut(&self.local_id) {
            entry.heartbeat = self.local_heartbeat;
            entry.last_seen_epoch_ms = now_ms;
            entry.status = NodeStatus::Alive;
        } else {
            self.peers.insert(
                self.local_id.clone(),
                PeerDescriptor {
                    id: self.local_id.clone(),
                    endpoint: self.local_endpoint.clone(),
                    status: NodeStatus::Alive,
                    heartbeat: self.local_heartbeat,
                    incarnation: self.local_incarnation,
                    last_seen_epoch_ms: now_ms,
                    metadata_json: "{}".to_string(),
                },
            );
        }
    }

    pub fn register_peer(
        &mut self,
        id: &str,
        endpoint: &str,
        metadata_json: &str,
        now_ms: u64,
    ) -> bool {
        if self.peers.len() >= MAX_MESH_PEERS && !self.peers.contains_key(id) {
            return false;
        }
        if let Some(existing) = self.peers.get_mut(id) {
            existing.endpoint = endpoint.to_string();
            existing.metadata_json = metadata_json.to_string();
            existing.last_seen_epoch_ms = now_ms;
            existing.status = NodeStatus::Alive;
        } else {
            self.peers.insert(
                id.to_string(),
                PeerDescriptor {
                    id: id.to_string(),
                    endpoint: endpoint.to_string(),
                    status: NodeStatus::Alive,
                    heartbeat: 1,
                    incarnation: 1,
                    last_seen_epoch_ms: now_ms,
                    metadata_json: metadata_json.to_string(),
                },
            );
        }
        true
    }

    pub fn process_digest(
        &mut self,
        peer_id: &str,
        heartbeat: u64,
        incarnation: u64,
        status: NodeStatus,
        now_ms: u64,
    ) -> bool {
        if peer_id == self.local_id {
            if (status == NodeStatus::Suspect || status == NodeStatus::Dead)
                && incarnation >= self.local_incarnation
            {
                self.local_incarnation = incarnation.saturating_add(1);
                self.local_heartbeat = self.local_heartbeat.saturating_add(1);
                if let Some(entry) = self.peers.get_mut(&self.local_id) {
                    entry.incarnation = self.local_incarnation;
                    entry.heartbeat = self.local_heartbeat;
                    entry.status = NodeStatus::Alive;
                    entry.last_seen_epoch_ms = now_ms;
                }
            }
            return true;
        }

        if let Some(existing) = self.peers.get_mut(peer_id) {
            if incarnation > existing.incarnation {
                existing.incarnation = incarnation;
                existing.heartbeat = heartbeat;
                existing.status = status;
                existing.last_seen_epoch_ms = now_ms;
                return true;
            }
            if incarnation == existing.incarnation && heartbeat > existing.heartbeat {
                existing.heartbeat = heartbeat;
                existing.status = status;
                existing.last_seen_epoch_ms = now_ms;
                return true;
            }
        }
        false
    }

    pub fn reap_stale_peers(
        &mut self,
        suspect_timeout_ms: u64,
        dead_timeout_ms: u64,
        now_ms: u64,
    ) -> usize {
        let mut transitions: usize = 0;
        for (id, peer) in &mut self.peers {
            if id == &self.local_id || peer.status == NodeStatus::Left {
                continue;
            }
            let elapsed = now_ms.saturating_sub(peer.last_seen_epoch_ms);
            if elapsed >= dead_timeout_ms && peer.status != NodeStatus::Dead {
                peer.status = NodeStatus::Dead;
                transitions = transitions.saturating_add(1);
            } else if elapsed >= suspect_timeout_ms && peer.status == NodeStatus::Alive {
                peer.status = NodeStatus::Suspect;
                transitions = transitions.saturating_add(1);
            }
        }
        transitions
    }

    #[must_use]
    pub fn select_gossip_targets(&mut self, count: usize) -> Vec<String> {
        let candidate_keys: Vec<String> = self
            .peers
            .iter()
            .filter(|(k, v)| k.as_str() != self.local_id && v.status == NodeStatus::Alive)
            .map(|(k, _)| k.clone())
            .collect();

        if candidate_keys.is_empty() || count == 0 {
            return Vec::new();
        }

        let total = candidate_keys.len();
        let target_count = count.min(total);
        let mut selected = Vec::with_capacity(target_count);

        for i in 0..target_count {
            let sum = self.rr_cursor.saturating_add(i);
            let idx = sum.checked_rem(total).unwrap_or(0);
            if let Some(target) = candidate_keys.get(idx) {
                selected.push(target.clone());
            }
        }
        let advance = self.rr_cursor.saturating_add(target_count);
        self.rr_cursor = advance.checked_rem(total).unwrap_or(0);
        selected
    }

    #[must_use]
    pub fn alive_peers_count(&self) -> usize {
        self.peers
            .values()
            .filter(|p| p.status == NodeStatus::Alive)
            .count()
    }

    #[must_use]
    pub fn total_peers_count(&self) -> usize {
        self.peers.len()
    }

    #[must_use]
    pub fn get_peer(&self, id: &str) -> Option<&PeerDescriptor> {
        self.peers.get(id)
    }

    #[must_use]
    pub fn export_membership_digest(&self) -> Vec<(String, u64, u64, String)> {
        self.peers
            .values()
            .map(|p| {
                (
                    p.id.clone(),
                    p.heartbeat,
                    p.incarnation,
                    p.status.as_str().to_string(),
                )
            })
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::{GossipMesh, NodeStatus};

    #[test]
    fn test_local_heartbeat_and_registration() {
        let mut mesh = GossipMesh::new("node-core", "192.168.1.100:9000");
        mesh.heartbeat(1000);
        assert_eq!(mesh.total_peers_count(), 1);
        assert_eq!(mesh.alive_peers_count(), 1);

        assert!(mesh.register_peer("sat-1", "192.168.1.101:9000", "{}", 1000));
        assert_eq!(mesh.total_peers_count(), 2);
        assert_eq!(mesh.alive_peers_count(), 2);
    }

    #[test]
    fn test_process_digest_and_refute_stale() {
        let mut mesh = GossipMesh::new("node-core", "192.168.1.100:9000");
        mesh.heartbeat(1000);
        mesh.register_peer("sat-1", "192.168.1.101:9000", "{}", 1000);

        let updated = mesh.process_digest("sat-1", 5, 1, NodeStatus::Alive, 2000);
        assert!(updated);
        let peer = mesh.get_peer("sat-1");
        assert_eq!(peer.map(|p| p.heartbeat), Some(5));

        mesh.process_digest("node-core", 10, 1, NodeStatus::Suspect, 2500);
        let local = mesh.get_peer("node-core");
        assert_eq!(local.map(|p| p.incarnation), Some(2));
        assert_eq!(local.map(|p| p.status), Some(NodeStatus::Alive));
    }

    #[test]
    fn test_reap_stale_peers_timeout() {
        let mut mesh = GossipMesh::new("node-core", "192.168.1.100:9000");
        mesh.heartbeat(1000);
        mesh.register_peer("sat-1", "192.168.1.101:9000", "{}", 1000);

        let transitions1 = mesh.reap_stale_peers(5000, 10000, 7000);
        assert_eq!(transitions1, 1);
        assert_eq!(
            mesh.get_peer("sat-1").map(|p| p.status),
            Some(NodeStatus::Suspect)
        );

        let transitions2 = mesh.reap_stale_peers(5000, 10000, 12000);
        assert_eq!(transitions2, 1);
        assert_eq!(
            mesh.get_peer("sat-1").map(|p| p.status),
            Some(NodeStatus::Dead)
        );
    }

    #[test]
    fn test_select_gossip_targets() {
        let mut mesh = GossipMesh::new("node-core", "192.168.1.100:9000");
        mesh.heartbeat(1000);
        mesh.register_peer("sat-1", "192.168.1.101:9000", "{}", 1000);
        mesh.register_peer("sat-2", "192.168.1.102:9000", "{}", 1000);

        let targets = mesh.select_gossip_targets(2);
        assert_eq!(targets.len(), 2);
    }
}
