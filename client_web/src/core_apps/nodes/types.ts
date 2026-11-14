export type HardwareTarget = 'pc' | 'raspberry' | 'esp32' | 'android';

export interface MeshNodeItem {
  id: string;
  name: string;
  tier: string;
  type: string;
  ip: string;
  status: string;
  online?: boolean;
  source?: 'local' | 'paired' | 'mesh';
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
  fingerprint?: string;
  pairing_code?: string;
  firmware?: string;
  flash_encrypted?: boolean;
}

export type ResourceLevel = 'calm' | 'elevated' | 'high' | 'critical';

export interface ResourceComponent {
  id: string;
  kind: string;
  class: string;
  rss: number;
  visible: boolean;
}

export interface ResourceAction {
  id: string;
  action: string;
  reason: string;
  reclaim: number;
  ok?: boolean;
}

export interface ResourceBudget {
  id: string;
  budget: number;
  rss: number;
  over: boolean;
}

export interface ResourceState {
  level: ResourceLevel;
  pressure: number;
  mem_percent: number;
  reclaim_total: number;
  system: { mem_total: number; mem_available: number; cpu_percent: number; gpu_percent: number; cores: number };
  components: ResourceComponent[];
  budgets: ResourceBudget[];
  applied: ResourceAction[];
  protected: string[];
}

export interface ResourceSnapshot {
  state: Partial<ResourceState>;
  history: { at: number; level: ResourceLevel; pressure: number }[];
  log: (ResourceAction & { at: number })[];
}
