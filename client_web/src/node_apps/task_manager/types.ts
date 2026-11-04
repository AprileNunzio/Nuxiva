export type ProcessCategory = 'ai_engine' | 'nuxiva' | 'system';

export interface SystemProcess {
  readonly pid: number;
  readonly name: string;
  readonly cpu_percent: number;
  readonly ram_mb: number;
  readonly gpu_memory_mb: number;
  readonly status: string;
  readonly user: string;
  readonly category: ProcessCategory;
}

export interface CpuStats {
  readonly percent: number;
  readonly cores: number;
  readonly freq_mhz: number;
}

export interface RamStats {
  readonly used_gb: number;
  readonly total_gb: number;
  readonly percent: number;
}

export interface GpuStats {
  readonly name: string;
  readonly memory_total_mb: number;
  readonly memory_used_mb: number;
  readonly utilization_percent: number;
  readonly temperature_c: number;
}

export interface NodeCapabilities {
  readonly voice_studio: boolean;
  readonly brain_llm: boolean;
  readonly vision_camera: boolean;
  readonly mesh_hub: boolean;
}

export interface NodeTasksSummary {
  readonly cpu: CpuStats;
  readonly ram: RamStats;
  readonly gpu: GpuStats | null;
  readonly processes: readonly SystemProcess[];
  readonly capabilities: NodeCapabilities;
}