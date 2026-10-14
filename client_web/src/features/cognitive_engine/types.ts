export type CognitiveEngineId =
  | 'nuxiva-4.2-legacy'
  | 'nuxiva-5.0-veloce'
  | 'nuxiva-5.0-empatico'
  | 'nuxiva-6.0-pro'
  | 'nuxiva-6.5-ultra'
  | 'nuxiva-6.5-auto';

export interface CognitiveEngineProfile {
  id: CognitiveEngineId;
  name: string;
  architecture: string;
  latency_sla_ms: number;
  vram_mb: number;
  active: boolean;
}

export interface EngineVersionStatusResponse {
  current_configured: CognitiveEngineId;
  active_runtime: CognitiveEngineId;
  latency_sla_ms: number;
  vram_mb: number;
  engines: CognitiveEngineProfile[];
  success: boolean;
}

export interface EngineTelemetryUpdate {
  version: CognitiveEngineId;
  synaptic_latency_ms: number;
  vram_allocated_mb: number;
  complexity_psi: number;
  neuromodulators: {
    dopamine: number;
    noradrenaline: number;
    serotonin: number;
    cortisol: number;
  };
}
