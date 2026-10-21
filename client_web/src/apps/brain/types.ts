export type ComputeMethod = 'api_key' | 'ollama_local' | 'ollama_remote';

export type BrainProviderType = ComputeMethod;

export type BrainTargetCategory = 'core_brain' | 'live_audio' | 'ceo' | 'agent';

export interface DiscoveredOllamaModel {
  readonly name: string;
  readonly sizeBytes: number;
  readonly parameterSize: string;
  readonly quantizationLevel: string;
  readonly family: string;
  readonly modifiedAt: string;
}

export interface RemoteOllamaServer {
  readonly id: string;
  readonly label: string;
  readonly rawInputHost: string;
  readonly normalizedBaseUrl: string;
  readonly status: 'idle' | 'checking' | 'online' | 'offline';
  readonly latencyMs: number | null;
  readonly lastCheckedAt: string | null;
  readonly availableModels: readonly DiscoveredOllamaModel[];
  readonly selectedModel: string;
  readonly errorMessage: string | null;
}

export interface RecommendedLocalModel {
  readonly id: string;
  readonly name: string;
  readonly cliCommand: string;
  readonly parameters: string;
  readonly activeParameters: string;
  readonly recommendedVramGb: number;
}

export interface BrainGlobalDefault {
  readonly provider: BrainProviderType;
  readonly serverId: string | null;
  readonly baseUrl: string;
  readonly modelName: string;
  readonly temperature: number;
  readonly contextWindow: string;
  readonly mcpToolsEnabled: readonly string[];
}

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
  readonly inheritsGlobalDefault?: boolean;
  readonly serverId?: string | null;
  readonly baseUrl?: string;
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
