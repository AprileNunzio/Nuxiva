export type HardwareTarget = 'pc' | 'raspberry' | 'esp32' | 'android';

export interface MeshNodeItem {
  id: string;
  name: string;
  tier: string;
  type: string;
  ip: string;
  status: string;
  parent_id?: string;
  is_remote_vpn?: boolean;
  telemetry?: {
    cpu_percent?: number;
    ram_used_gb?: number;
    ram_total_gb?: number;
    temp_c?: number;
    ping_ms?: number;
  };
}

export interface UsbPort {
  device: string;
  description: string;
}

export interface OnboardPayload {
  target: HardwareTarget;
  name: string;
  parent_id: string;
  parent_ip: string;
  usb_port?: string;
  wifi_ssid?: string;
  wifi_key?: string;
  root_user?: string;
  root_password?: string;
}

export interface OnboardResponse {
  node_id: string;
  name: string;
  target: HardwareTarget;
  tier: string;
  status: string;
  parent_id: string;
  message: string;
  log?: string;
}
