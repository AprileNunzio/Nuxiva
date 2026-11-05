use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum AdapterKind {
    Ethernet,
    WiFi,
    Loopback,
    Virtual,
    Unknown,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct NetworkAdapter {
    pub name: String,
    pub mac_address: String,
    pub ip_addresses: Vec<String>,
    pub kind: AdapterKind,
    pub is_up: bool,
    pub is_loopback: bool,
    pub speed_mbps: Option<u64>,
    pub rx_bytes: u64,
    pub tx_bytes: u64,
    pub rx_errors: u64,
    pub tx_errors: u64,
}

impl NetworkAdapter {
    #[must_use]
    pub fn new(name: impl Into<String>, mac: impl Into<String>, kind: AdapterKind) -> Self {
        Self {
            name: name.into(),
            mac_address: mac.into(),
            ip_addresses: Vec::new(),
            kind,
            is_up: false,
            is_loopback: false,
            speed_mbps: None,
            rx_bytes: 0,
            tx_bytes: 0,
            rx_errors: 0,
            tx_errors: 0,
        }
    }

    #[must_use]
    pub fn with_ip(mut self, ip: impl Into<String>) -> Self {
        self.ip_addresses.push(ip.into());
        self
    }

    pub fn set_state(&mut self, is_up: bool) {
        self.is_up = is_up;
    }

    pub fn update_counters(&mut self, rx: u64, tx: u64, rx_err: u64, tx_err: u64) {
        self.rx_bytes = rx;
        self.tx_bytes = tx;
        self.rx_errors = rx_err;
        self.tx_errors = tx_err;
    }

    #[must_use]
    pub const fn has_errors(&self) -> bool {
        self.rx_errors > 0 || self.tx_errors > 0
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct NetworkManager {
    adapters: Vec<NetworkAdapter>,
}

impl NetworkManager {
    #[must_use]
    pub fn new() -> Self {
        Self {
            adapters: Vec::new(),
        }
    }

    pub fn register_adapter(&mut self, adapter: NetworkAdapter) {
        if let Some(existing) = self.adapters.iter_mut().find(|a| a.name == adapter.name) {
            *existing = adapter;
        } else {
            self.adapters.push(adapter);
        }
    }

    #[must_use]
    pub fn adapter(&self, name: &str) -> Option<&NetworkAdapter> {
        self.adapters.iter().find(|a| a.name == name)
    }

    #[must_use]
    pub fn adapters(&self) -> &[NetworkAdapter] {
        &self.adapters
    }

    #[must_use]
    pub fn active_adapters(&self) -> Vec<&NetworkAdapter> {
        self.adapters
            .iter()
            .filter(|a| a.is_up && !a.is_loopback)
            .collect()
    }

    #[must_use]
    pub fn total_throughput(&self) -> (u64, u64) {
        let (rx, tx) = self.adapters.iter().fold((0u64, 0u64), |acc, a| {
            (
                acc.0.saturating_add(a.rx_bytes),
                acc.1.saturating_add(a.tx_bytes),
            )
        });
        (rx, tx)
    }

    #[must_use]
    pub fn find_by_ip(&self, ip: &str) -> Option<&NetworkAdapter> {
        self.adapters
            .iter()
            .find(|a| a.ip_addresses.iter().any(|addr| addr == ip))
    }

    pub fn remove_adapter(&mut self, name: &str) -> bool {
        if let Some(pos) = self.adapters.iter().position(|a| a.name == name) {
            self.adapters.remove(pos);
            true
        } else {
            false
        }
    }

    #[must_use]
    pub fn is_healthy(&self) -> bool {
        let active = self.active_adapters();
        if active.is_empty() {
            return false;
        }
        !active.iter().any(|a| a.has_errors())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_adapter_creation_and_counters() {
        let mut eth0 = NetworkAdapter::new("eth0", "00:11:22:33:44:55", AdapterKind::Ethernet)
            .with_ip("192.168.1.100");
        assert_eq!(eth0.name, "eth0");
        assert_eq!(eth0.ip_addresses.len(), 1);
        assert!(!eth0.is_up);
        assert!(!eth0.has_errors());

        eth0.set_state(true);
        eth0.update_counters(1024, 2048, 0, 1);
        assert!(eth0.is_up);
        assert!(eth0.has_errors());
        assert_eq!(eth0.rx_bytes, 1024);
        assert_eq!(eth0.tx_bytes, 2048);
    }

    #[test]
    fn test_network_manager_workflow() {
        let mut mgr = NetworkManager::new();
        assert!(!mgr.is_healthy());

        let mut eth0 = NetworkAdapter::new("eth0", "00:11:22:33:44:55", AdapterKind::Ethernet)
            .with_ip("192.168.1.50");
        eth0.set_state(true);
        eth0.update_counters(500, 1000, 0, 0);

        let mut lo = NetworkAdapter::new("lo", "00:00:00:00:00:00", AdapterKind::Loopback)
            .with_ip("127.0.0.1");
        lo.is_loopback = true;
        lo.set_state(true);

        mgr.register_adapter(eth0);
        mgr.register_adapter(lo);

        assert_eq!(mgr.adapters().len(), 2);
        assert_eq!(mgr.active_adapters().len(), 1);
        assert_eq!(mgr.total_throughput(), (500, 1000));
        assert!(mgr.is_healthy());

        let found = mgr.find_by_ip("192.168.1.50");
        assert!(found.is_some());
        assert_eq!(found.map(|a| a.name.as_str()), Some("eth0"));

        let not_found = mgr.find_by_ip("10.0.0.1");
        assert!(not_found.is_none());

        assert!(mgr.remove_adapter("eth0"));
        assert_eq!(mgr.adapters().len(), 1);
        assert!(!mgr.is_healthy());
    }
}
