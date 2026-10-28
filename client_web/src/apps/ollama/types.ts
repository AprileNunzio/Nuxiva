export interface CpuSpecs {
  model: string;
  physical_cores: number;
  logical_cores: number;
  has_avx2: boolean;
  has_avx512: boolean;
}

export interface MemorySpecs {
  total_bytes: number;
  total_gb: number;
  available_gb: number;
}

export interface GpuSpecs {
  name: string;
  vram_total_gb: number;
  vram_free_gb: number;
  backend: string;
  is_supported: boolean;
}

export interface HardwareProfile {
  tier: 'lightweight' | 'balanced' | 'enterprise';
  cpu: CpuSpecs;
  memory: MemorySpecs;
  gpu: GpuSpecs | null;
  recommended_parallel: number;
  recommended_context: number;
  recommended_max_tokens: number;
  recommended_loaded_models: number;
  recommended_flash_attention: boolean;
  recommended_threads: number;
}

export interface OllamaConfig {
  num_parallel: number;
  num_ctx: number;
  num_predict: number;
  max_loaded_models: number;
  flash_attention: boolean;
  keep_alive: string;
  cpu_weight: number;
  nice: number;
  num_thread: number;
  max_queue: number;
  mode: string;
}

export interface DaemonStatus {
  online: boolean;
  version: string;
  active_models: string[];
  host: string;
  config: OllamaConfig;
  hardware: HardwareProfile;
}

export interface BenchmarkResult {
  model: string;
  prompt_tokens: number;
  generated_tokens: number;
  total_duration_ms: number;
  eval_duration_ms: number;
  tokens_per_second: number;
  time_to_first_token_ms: number;
}
