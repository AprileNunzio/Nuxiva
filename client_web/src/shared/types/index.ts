export type NavigationTab = 'MESH_CANVAS' | 'CORE_APPS' | 'NODE_CONTROL' | 'CORE' | 'WORLD_3D' | 'STUDIO_3D' | 'CONTROL_DECK';

export type NodeTier = 'Tier-0 (Virtual Core)' | 'Tier-1 (Compute & Core)' | 'Tier-2 (Smart Edge Satellite)' | 'Tier-3 (Pure Micro-Satellite)';

export interface MeshNodeTelemetry {
  node_id: string;
  name: string;
  tier: string;
  cpu_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  gpu_name?: string;
  vram_used_gb?: number;
  vram_total_gb?: number;
  active_model?: string;
  power_watts: number;
  temp_c: number;
  ping_ms: number;
  tx_kbps: number;
  rx_kbps: number;
  child_satellites?: string[];
  status: string;
  is_remote_vpn?: boolean;
  stream?: string;
  last_updated: number;
}

export interface MeshTopologyNode {
  id: string;
  name: string;
  tier: string;
  type: 'core' | 'compute' | 'satellite' | 'micro' | 'mobile';
  ip: string;
  parent_id?: string;
  is_remote_vpn?: boolean;
  x?: number;
  y?: number;
  telemetry: MeshNodeTelemetry | Record<string, unknown>;
}

export interface MeshTopologyLink {
  source: string;
  target: string;
  protocol: string;
}

export interface MeshTopologyState {
  nodes: MeshTopologyNode[];
  links: MeshTopologyLink[];
  timestamp: number;
}

export interface SpatialAsset {
  id: string;
  name: string;
  category: 'weather' | 'tools' | 'furniture' | 'architecture' | 'vehicles' | 'devices' | 'fx';
  tags: string[];
  icon: string;
  description: string;
  scale?: number;
}

export interface WorldEnvironmentState {
  weather: 'CLEAR' | 'RAIN' | 'SNOW' | 'THUNDERSTORM' | 'NIGHT_NEON';
  sceneTheme: 'CYBER_LAB' | 'MODERN_OFFICE' | 'PANORAMIC_TERRACE' | 'HOLODECK_VOID';
  equippedItem: string | null;
  ambientLightColor: string;
  rainIntensity: number;
}

export interface KnowledgeNode {
  id: string;
  node_type: string;
  label: string;
  properties: Record<string, unknown>;
  created_at: number;
  updated_at: number;
}

export interface KnowledgeEdge {
  source_id: string;
  target_id: string;
  relation_type: string;
  weight: number;
  properties: Record<string, unknown>;
}

export interface GraphSnapshot {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
}

export interface AgentDescriptor {
  id: string;
  name: string;
  status: 'IDLE' | 'EXECUTING' | 'ERROR';
  capabilities: string[];
  latencyMs: number;
}

export interface SystemModelConfig {
  activeProvider: 'OLLAMA' | 'OPENAI' | 'ANTHROPIC' | 'GEMINI';
  ollamaModel: string;
  temperature: number;
  maxTokens: number;
  voiceVolume: number;
  voiceSpeed: number;
}
