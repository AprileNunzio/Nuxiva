export interface AcceptanceCriteria {
  description: string;
  target?: string;
  verified: boolean;
  evidence?: string;
}

export interface Task {
  id: string;
  phase_id: string;
  title: string;
  description: string;
  specialist_id: string;
  specialist_role: string;
  depends_on: string[];
  status: 'pending' | 'running' | 'review' | 'waiting' | 'done' | 'failed';
  round: number;
  feedback?: string;
  criteria: AcceptanceCriteria[];
  result?: string;
  error?: string;
}

export interface Phase {
  id: string;
  title: string;
  description: string;
  tasks: Task[];
  status: string;
}

export interface Specialist {
  id: string;
  role: string;
  title: string;
  mission_role: string;
  capabilities: string[];
  tools: string[];
  is_dynamic: boolean;
}

export interface MissionQuestion {
  id: string;
  question: string;
  options: string[];
  is_multi_select: boolean;
  answered: boolean;
  answer?: string;
  selected_options?: string[];
  rationale?: string;
}

export interface CollabMessage {
  id: string;
  sender_id: string;
  sender_role: string;
  target_id: string;
  channel: string;
  content: string;
  kind: string;
  artifact_ref?: string;
  timestamp: number;
}

export interface EpisodicMemory {
  summary: string;
  lessons_learned: string[];
  key_decisions: string[];
  last_compressed_at: number;
  compression_count: number;
}

export interface AgentInferenceProfile {
  agent_id: string;
  label: string;
  provider: 'auto_fallback' | 'ollama' | 'cloud';
  endpoint: string;
  model: string;
  temperature: number;
  timeout_seconds: number;
}

export interface MissionArtifact {
  id: string;
  title: string;
  kind: string;
  relative_path: string;
  checksum: string;
  size_bytes: number;
  generated_by: string;
  timestamp: number;
}

export interface Mission {
  id: string;
  title: string;
  goal: string;
  domain: string;
  lang: string;
  directives: string[];
  options: Record<string, string>;
  phases: Phase[];
  specialists: Specialist[];
  questions: MissionQuestion[];
  collab_messages: CollabMessage[];
  artifacts: MissionArtifact[];
  memory?: EpisodicMemory;
  status: 'planning' | 'question' | 'running' | 'paused' | 'done' | 'failed' | 'cancelled';
  progress: number;
  error?: string;
  workspace?: string;
  created_at: number;
  updated_at: number;
}

export interface RuntimeConfig {
  mode: 'auto_fallback' | 'ollama' | 'cloud';
  ollama_endpoint: string;
  ollama_model: string;
  cloud_model?: string;
  token_rate_limit_per_min: number;
  max_concurrent_requests: number;
  request_timeout_seconds: number;
  offline_cache_enabled: boolean;
}

export interface RuntimeHealth {
  healthy: boolean;
  mode: string;
  latency_ms: number;
  ollama_available: boolean;
  ollama_models: string[];
  cloud_available: boolean;
  timestamp: number;
}

export interface MissionAutomation {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  ephemeral?: boolean;
  mission_id?: string;
  triggers: Array<{ type: string; every?: number; unit?: string; name?: string }>;
  actions: Array<{ type: string; channels?: string[]; count?: number; entity?: string }>;
  runs?: number;
  last_run?: number;
}

export interface WatchdogPayload {
  interval_minutes: number;
  channels: string[];
  enabled: boolean;
}
