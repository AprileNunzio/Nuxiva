export interface CloudProvider {
  id: string;
  name: string;
  base_url: string;
  default_model: string;
  models: string[];
}

export interface RemoteOllamaInstance {
  id: string;
  name: string;
  host_url: string;
  model: string;
  task: 'fast_chat' | 'deep_reasoning' | 'vision' | 'coder' | 'audio_transcription' | 'embeddings' | 'batch_worker' | string;
  node_id?: string;
  latency_ms?: number;
  status?: 'online' | 'offline' | 'unknown';
}

export interface CloudSlotConfig {
  provider: string;
  model: string;
  api_key: string;
  base_url: string;
  label?: string;
  target_latency?: string;
}

export interface LocalOllamaStatus {
  installed: boolean;
  running: boolean;
  binary_path?: string;
  version?: string;
  models: string[];
  catalog?: string[];
}

export interface BrainConfig {
  nodeId: string;
  enabled: boolean;
  settings: {
    mode: 'local_ollama' | 'remote_ollama' | 'cloud_llm';
    local_model: string;
    remote_node_id?: string;
    remote_host?: string;
    remote_model?: string;
    cloud_provider: string;
    cloud_model: string;
    cloud_api_key: string;
    cloud_base_url: string;
    system_prompt: string;
    temperature: number;
    max_tokens: number;
    fallback_enabled: boolean;
    fallback_provider: string;
    cloud_slots?: Record<string, CloudSlotConfig>;
    remote_mesh_instances?: RemoteOllamaInstance[];
  };
  updatedAt: string;
}

export interface TestResult {
  success: boolean;
  latency_ms: number;
  reply?: string;
  tokens?: number;
  tokens_per_sec?: number;
  model?: string;
  host?: string;
  provider?: string;
  error?: string;
}
