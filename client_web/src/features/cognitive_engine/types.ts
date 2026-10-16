export type CognitiveEngineId =
  | 'nuxiva-4.2-legacy'
  | 'nuxiva-5.0-veloce'
  | 'nuxiva-5.0-empatico'
  | 'nuxiva-6.0-pro'
  | 'nuxiva-6.5-ultra'
  | 'nuxiva-6.5-auto';

export type EnginePick = 'sequential' | 'first' | 'best';

export interface EngineStrategy {
  kind: 'chat' | 'deep';
  candidates: number;
  pick: EnginePick;
  critic: boolean;
  wait_s: number;
}

export interface CognitiveEngineProfile {
  id: CognitiveEngineId;
  name: string;
  architecture: string;
  strategy: EngineStrategy;
  active: boolean;
}

export interface EngineVersionStatusResponse {
  current_configured: CognitiveEngineId;
  engines: CognitiveEngineProfile[];
  success: boolean;
}
