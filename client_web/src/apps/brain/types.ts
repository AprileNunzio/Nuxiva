export type ComputeMethod = 'api_key' | 'ollama_local' | 'ollama_remote';

export type BrainTargetCategory = 'core_brain' | 'live_audio' | 'ceo' | 'agent';

export interface BrainTargetConfig {
  readonly id: string;
  readonly name: string;
  readonly roleKey: string;
  readonly descriptionKey: string;
  readonly category: BrainTargetCategory;
  readonly method: ComputeMethod;
  readonly assignedModel: string;
  readonly providerId?: string;
  readonly remoteHost?: string;
  readonly remotePort?: number;
  readonly localMachineId?: string;
  readonly temperature: number;
  readonly contextWindow?: string;
  readonly mcpToolsEnabled: readonly string[];
  readonly status: 'ready' | 'connected' | 'downloading' | 'offline' | 'needs_config';
  readonly latencyMs?: number;
  readonly speedTokensSec?: number;
  readonly avatarIcon?: string;
  readonly accentColor?: string;
}

export interface ModelSpec {
  readonly id: string;
  readonly name: string;
  readonly provider: string;
  readonly type: 'cloud' | 'local' | 'remote_ollama';
  readonly contextWindow: string;
  readonly latencyMs: number;
  readonly speedTokensSec?: number;
  readonly capabilities: readonly ('reasoning' | 'vision' | 'code' | 'tools')[];
  readonly notes: string;
  readonly sizeGb?: number;
  readonly vramRequiredMb?: number;
}

export interface LlmProvider {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly iconName: string;
  readonly apiKey?: string;
  readonly endpointUrl?: string;
  readonly isConfigured: boolean;
  readonly defaultEndpoint?: string;
  readonly models: readonly ModelSpec[];
}

export interface OllamaMachine {
  readonly id: string;
  readonly name: string;
  readonly ip?: string;
  readonly ramGb: number;
  readonly cores: number;
  readonly gpu: string;
  readonly vramGb: number;
  readonly os: string;
  readonly isLocal: boolean;
  readonly ollamaInstalled: boolean;
  readonly ollamaVersion?: string;
  readonly installedModels: readonly string[];
}

export interface DownloadableModel {
  readonly id: string;
  readonly name: string;
  readonly tag: string;
  readonly sizeGb: number;
  readonly vramRequiredGb: number;
  readonly minRamGb: number;
  readonly capabilities: readonly ('reasoning' | 'vision' | 'code' | 'tools')[];
  readonly recommendedFor: string;
  readonly isInstalled?: boolean;
}

export interface McpToolDefinition {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly iconName: string;
  readonly category: 'smart_home' | 'filesystem' | 'search' | 'system' | 'memory' | 'science';
}
