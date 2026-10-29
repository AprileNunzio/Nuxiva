export type ConnectionRoutingPolicy = 'ethernet_only' | 'wifi_only' | 'dual_aggregation' | 'fallback';

export type InterfaceKind = 'ethernet' | 'wifi' | 'cellular_gsm' | 'vpn' | 'virtual';

export type IpAssignmentMode = 'dhcp' | 'static';

export interface NetworkInterface {
  readonly name: string;
  readonly kind: InterfaceKind;
  readonly mac_address: string;
  readonly ipv4: string | null;
  readonly netmask: string | null;
  readonly gateway: string | null;
  readonly dns_primary: string | null;
  readonly dns_secondary: string | null;
  readonly ip_mode: IpAssignmentMode;
  readonly is_up: boolean;
  readonly speed_mbps: number | null;
  readonly mtu: number;
  readonly rx_bytes: number;
  readonly tx_bytes: number;
  readonly signal_percent: number | null;
}

export interface GsmModem {
  readonly modem_id: string;
  readonly operator: string;
  readonly technology: string;
  readonly signal_bars: number;
  readonly signal_dbm: number;
  readonly apn: string;
  readonly roaming_enabled: boolean;
  readonly emergency_fallback_only: boolean;
  readonly is_connected: boolean;
}

export interface VpnTunnel {
  readonly enabled: boolean;
  readonly tunnel_name: string;
  readonly virtual_ip: string;
  readonly endpoint: string;
  readonly handshake_age_secs: number | null;
  readonly bytes_transferred: number;
}

export interface ActiveRouteResult {
  readonly primary_interface: string;
  readonly secondary_interface: string | null;
  readonly status: string;
  readonly failover_triggered: boolean;
  readonly internet_reachable: boolean;
}

export interface NodeNetworkProfile {
  readonly node_id: string;
  readonly policy: ConnectionRoutingPolicy;
  readonly interfaces: readonly NetworkInterface[];
  readonly gsm_modem: GsmModem | null;
  readonly vpn: VpnTunnel | null;
  readonly active_route: ActiveRouteResult;
}

export interface IpConfigPayload {
  readonly mode: IpAssignmentMode;
  readonly ipv4?: string | null;
  readonly netmask?: string | null;
  readonly gateway?: string | null;
  readonly dns_primary?: string | null;
  readonly dns_secondary?: string | null;
}

export interface WifiNetwork {
  readonly ssid: string;
  readonly bssid: string;
  readonly signal: number;
  readonly security: string;
  readonly frequency: string;
  readonly is_connected: boolean;
}

export interface WifiScanResult {
  readonly networks: readonly WifiNetwork[];
  readonly radio_enabled: boolean;
  readonly current_ssid: string | null;
  readonly interface: string;
}

export interface WifiConnectPayload {
  readonly ssid: string;
  readonly password?: string;
  readonly interface?: string;
}

export interface WifiRadioPayload {
  readonly enabled: boolean;
  readonly interface?: string;
}
