export interface SanEntry {
  kind: 'dns' | 'ip' | 'uri';
  value: string;
  category: 'loopback' | 'tailscale' | 'vpn' | 'ip' | 'dns';
}

export interface NetworkInterfaceInfo {
  name: string;
  addresses: string[];
  is_tailscale: boolean;
  is_vpn: boolean;
}

export interface PkiStatus {
  has_ca: boolean;
  ca_subject: string;
  ca_fingerprint: string;
  ca_expires_at: string;
  has_server_cert: boolean;
  server_fingerprint: string;
  server_expires_at: string;
  sans: SanEntry[];
  interfaces: NetworkInterfaceInfo[];
  tailscale_detected: boolean;
  vpn_detected: boolean;
}

export interface PkiGenerateOptions {
  renew_ca?: boolean;
  organization?: string;
  custom_dns?: string[];
  custom_ips?: string[];
  include_tailscale?: boolean;
  include_vpn?: boolean;
}
