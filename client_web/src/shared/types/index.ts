export type NavigationTab = 'CORE' | 'WORLD_3D' | 'STUDIO_3D' | 'CONTROL_DECK';

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
