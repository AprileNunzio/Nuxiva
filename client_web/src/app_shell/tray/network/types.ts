export interface NetworkInterface {
  name: string;
  kind: 'wifi' | 'ethernet' | 'cellular_gsm' | 'vpn' | string;
  mac_address: string;
  ipv4: string | null;
  netmask: string | null;
  gateway: string | null;
  dns_primary: string | null;
  dns_secondary: string | null;
  ip_mode: string;
  is_up: boolean;
  speed_mbps: number;
  mtu: number;
  rx_bytes: number;
  tx_bytes: number;
  signal_percent: number | null;
}

export interface ActiveRoute {
  primary_interface: string;
  secondary_interface?: string | null;
  status: string;
  failover_triggered?: boolean;
  internet_reachable: boolean;
}

export interface NetworkProfile {
  node_id: string;
  policy: string;
  interfaces: NetworkInterface[];
  active_route: ActiveRoute;
}

export interface WifiNetwork {
  ssid: string;
  bssid: string;
  signal: number;
  security: string;
  frequency: string;
  is_connected: boolean;
}

export interface WifiScanResult {
  networks: WifiNetwork[];
  radio_enabled: boolean;
  current_ssid: string | null;
  interface: string;
}
