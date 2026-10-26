use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ConnectionRoutingPolicy {
    EthernetOnly,
    WifiOnly,
    DualAggregation,
    Fallback,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InterfaceKind {
    Ethernet,
    Wifi,
    CellularGsm,
    Vpn,
    Virtual,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum IpAssignmentMode {
    Dhcp,
    Static,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NetworkInterface {
    pub name: String,
    pub kind: InterfaceKind,
    pub mac_address: String,
    pub ipv4: Option<String>,
    pub netmask: Option<String>,
    pub gateway: Option<String>,
    pub dns_primary: Option<String>,
    pub dns_secondary: Option<String>,
    pub ip_mode: IpAssignmentMode,
    pub is_up: bool,
    pub speed_mbps: Option<u32>,
    pub mtu: u32,
    pub rx_bytes: u64,
    pub tx_bytes: u64,
    pub signal_percent: Option<u8>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GsmModem {
    pub modem_id: String,
    pub operator: String,
    pub technology: String,
    pub signal_bars: u8,
    pub signal_dbm: i32,
    pub apn: String,
    pub roaming_enabled: bool,
    pub emergency_fallback_only: bool,
    pub is_connected: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct VpnTunnel {
    pub enabled: bool,
    pub tunnel_name: String,
    pub virtual_ip: String,
    pub endpoint: String,
    pub handshake_age_secs: Option<u64>,
    pub bytes_transferred: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NodeNetworkProfile {
    pub node_id: String,
    pub policy: ConnectionRoutingPolicy,
    pub interfaces: Vec<NetworkInterface>,
    pub gsm_modem: Option<GsmModem>,
    pub vpn: VpnTunnel,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ActiveRouteResult {
    pub primary_interface: String,
    pub secondary_interface: Option<String>,
    pub status: String,
    pub failover_triggered: bool,
    pub internet_reachable: bool,
}

#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
pub struct NetworkGovernor {
    profiles: HashMap<String, NodeNetworkProfile>,
}

impl NetworkGovernor {
    #[must_use]
    pub fn new() -> Self {
        Self {
            profiles: HashMap::new(),
        }
    }

    pub fn register_or_update_profile(&mut self, profile: NodeNetworkProfile) {
        self.profiles.insert(profile.node_id.clone(), profile);
    }

    #[must_use]
    pub fn get_profile(&self, node_id: &str) -> Option<&NodeNetworkProfile> {
        self.profiles.get(node_id)
    }

    pub fn set_policy(&mut self, node_id: &str, policy: ConnectionRoutingPolicy) -> bool {
        let Some(prof) = self.profiles.get_mut(node_id) else {
            return false;
        };
        prof.policy = policy;
        true
    }

    pub fn toggle_interface(&mut self, node_id: &str, interface_name: &str, is_up: bool) -> bool {
        let Some(prof) = self.profiles.get_mut(node_id) else {
            return false;
        };
        for iface in &mut prof.interfaces {
            if iface.name == interface_name {
                iface.is_up = is_up;
                return true;
            }
        }
        false
    }

    pub fn toggle_vpn(&mut self, node_id: &str, enabled: bool) -> bool {
        let Some(prof) = self.profiles.get_mut(node_id) else {
            return false;
        };
        prof.vpn.enabled = enabled;
        true
    }

    #[allow(clippy::too_many_arguments)]
    pub fn update_interface_ip_config(
        &mut self,
        node_id: &str,
        interface_name: &str,
        mode: IpAssignmentMode,
        ipv4: Option<String>,
        netmask: Option<String>,
        gateway: Option<String>,
        dns_primary: Option<String>,
        dns_secondary: Option<String>,
    ) -> Result<(), String> {
        let Some(prof) = self.profiles.get_mut(node_id) else {
            return Err("node_not_found".to_string());
        };

        if mode == IpAssignmentMode::Static {
            let Some(ref ip) = ipv4 else {
                return Err("missing_static_ip".to_string());
            };
            if !Self::is_valid_ipv4(ip) {
                return Err("invalid_ipv4_format".to_string());
            }
        }

        for iface in &mut prof.interfaces {
            if iface.name == interface_name {
                iface.ip_mode = mode;
                if mode == IpAssignmentMode::Static {
                    iface.ipv4 = ipv4;
                    iface.netmask = netmask;
                    iface.gateway = gateway;
                    iface.dns_primary = dns_primary;
                    iface.dns_secondary = dns_secondary;
                }
                return Ok(());
            }
        }

        Err("interface_not_found".to_string())
    }

    #[must_use]
    pub fn is_valid_ipv4(ip: &str) -> bool {
        let segments: Vec<&str> = ip.trim().split('.').collect();
        if segments.len() != 4 {
            return false;
        }
        for seg in segments {
            let Ok(val) = seg.parse::<u16>() else {
                return false;
            };
            if val > 255 {
                return false;
            }
        }
        true
    }

    #[must_use]
    #[allow(clippy::too_many_lines)]
    pub fn determine_active_route(&self, node_id: &str) -> ActiveRouteResult {
        let Some(prof) = self.profiles.get(node_id) else {
            return ActiveRouteResult {
                primary_interface: "none".to_string(),
                secondary_interface: None,
                status: "node_offline".to_string(),
                failover_triggered: false,
                internet_reachable: false,
            };
        };

        let eth = prof
            .interfaces
            .iter()
            .find(|i| i.kind == InterfaceKind::Ethernet && i.is_up);
        let wifi = prof
            .interfaces
            .iter()
            .find(|i| i.kind == InterfaceKind::Wifi && i.is_up);
        let gsm = prof
            .gsm_modem
            .as_ref()
            .filter(|m| m.is_connected && m.signal_bars > 0);

        match prof.policy {
            ConnectionRoutingPolicy::EthernetOnly => {
                if let Some(e) = eth {
                    ActiveRouteResult {
                        primary_interface: e.name.clone(),
                        secondary_interface: None,
                        status: "ethernet_active".to_string(),
                        failover_triggered: false,
                        internet_reachable: true,
                    }
                } else {
                    ActiveRouteResult {
                        primary_interface: "none".to_string(),
                        secondary_interface: None,
                        status: "ethernet_disconnected".to_string(),
                        failover_triggered: false,
                        internet_reachable: false,
                    }
                }
            }
            ConnectionRoutingPolicy::WifiOnly => {
                if let Some(w) = wifi {
                    ActiveRouteResult {
                        primary_interface: w.name.clone(),
                        secondary_interface: None,
                        status: "wifi_active".to_string(),
                        failover_triggered: false,
                        internet_reachable: true,
                    }
                } else {
                    ActiveRouteResult {
                        primary_interface: "none".to_string(),
                        secondary_interface: None,
                        status: "wifi_disconnected".to_string(),
                        failover_triggered: false,
                        internet_reachable: false,
                    }
                }
            }
            ConnectionRoutingPolicy::DualAggregation => {
                if let (Some(e), Some(w)) = (eth, wifi) {
                    ActiveRouteResult {
                        primary_interface: e.name.clone(),
                        secondary_interface: Some(w.name.clone()),
                        status: "dual_aggregation_active".to_string(),
                        failover_triggered: false,
                        internet_reachable: true,
                    }
                } else if let Some(e) = eth {
                    ActiveRouteResult {
                        primary_interface: e.name.clone(),
                        secondary_interface: None,
                        status: "partial_aggregation_ethernet_only".to_string(),
                        failover_triggered: false,
                        internet_reachable: true,
                    }
                } else if let Some(w) = wifi {
                    ActiveRouteResult {
                        primary_interface: w.name.clone(),
                        secondary_interface: None,
                        status: "partial_aggregation_wifi_only".to_string(),
                        failover_triggered: false,
                        internet_reachable: true,
                    }
                } else {
                    ActiveRouteResult {
                        primary_interface: "none".to_string(),
                        secondary_interface: None,
                        status: "aggregation_down".to_string(),
                        failover_triggered: false,
                        internet_reachable: false,
                    }
                }
            }
            ConnectionRoutingPolicy::Fallback => {
                if let Some(e) = eth {
                    ActiveRouteResult {
                        primary_interface: e.name.clone(),
                        secondary_interface: wifi.map(|w| w.name.clone()),
                        status: "ethernet_primary_optimal".to_string(),
                        failover_triggered: false,
                        internet_reachable: true,
                    }
                } else if let Some(w) = wifi {
                    ActiveRouteResult {
                        primary_interface: w.name.clone(),
                        secondary_interface: gsm.map(|m| m.modem_id.clone()),
                        status: "failover_to_wifi".to_string(),
                        failover_triggered: true,
                        internet_reachable: true,
                    }
                } else if let Some(g) = gsm {
                    ActiveRouteResult {
                        primary_interface: g.modem_id.clone(),
                        secondary_interface: None,
                        status: "failover_to_cellular_emergency".to_string(),
                        failover_triggered: true,
                        internet_reachable: true,
                    }
                } else {
                    ActiveRouteResult {
                        primary_interface: "none".to_string(),
                        secondary_interface: None,
                        status: "all_interfaces_offline".to_string(),
                        failover_triggered: true,
                        internet_reachable: false,
                    }
                }
            }
        }
    }

    #[must_use]
    pub fn get_default_profile(node_id: &str, node_ip: Option<&str>) -> NodeNetworkProfile {
        let assigned_ip = node_ip.unwrap_or("192.168.1.50");
        NodeNetworkProfile {
            node_id: node_id.to_string(),
            policy: ConnectionRoutingPolicy::Fallback,
            interfaces: vec![
                NetworkInterface {
                    name: "eth0".to_string(),
                    kind: InterfaceKind::Ethernet,
                    mac_address: "e4:5f:01:aa:22:11".to_string(),
                    ipv4: Some(assigned_ip.to_string()),
                    netmask: Some("255.255.255.0".to_string()),
                    gateway: Some("192.168.1.1".to_string()),
                    dns_primary: Some("1.1.1.1".to_string()),
                    dns_secondary: Some("8.8.8.8".to_string()),
                    ip_mode: IpAssignmentMode::Dhcp,
                    is_up: true,
                    speed_mbps: Some(1000),
                    mtu: 1500,
                    rx_bytes: 412_580_000,
                    tx_bytes: 189_420_000,
                    signal_percent: None,
                },
                NetworkInterface {
                    name: "wlan0".to_string(),
                    kind: InterfaceKind::Wifi,
                    mac_address: "e4:5f:01:aa:22:12".to_string(),
                    ipv4: Some("192.168.1.155".to_string()),
                    netmask: Some("255.255.255.0".to_string()),
                    gateway: Some("192.168.1.1".to_string()),
                    dns_primary: Some("1.1.1.1".to_string()),
                    dns_secondary: Some("8.8.8.8".to_string()),
                    ip_mode: IpAssignmentMode::Dhcp,
                    is_up: true,
                    speed_mbps: Some(866),
                    mtu: 1500,
                    rx_bytes: 98_210_000,
                    tx_bytes: 45_120_000,
                    signal_percent: Some(92),
                },
            ],
            gsm_modem: Some(GsmModem {
                modem_id: "wwan0".to_string(),
                operator: "Nuxiva Mesh Cellular (LTE/5G)".to_string(),
                technology: "5G NSA".to_string(),
                signal_bars: 4,
                signal_dbm: -74,
                apn: "internet.mesh".to_string(),
                roaming_enabled: false,
                emergency_fallback_only: true,
                is_connected: true,
            }),
            vpn: VpnTunnel {
                enabled: true,
                tunnel_name: "wg0-mesh".to_string(),
                virtual_ip: "10.42.0.12/24".to_string(),
                endpoint: "mesh.nuxiva.internal:51820".to_string(),
                handshake_age_secs: Some(14),
                bytes_transferred: 325_400_000,
            },
        }
    }
}
