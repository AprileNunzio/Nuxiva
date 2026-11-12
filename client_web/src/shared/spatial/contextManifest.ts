export type AssistantMorphology =
  | 'CORE_HERO'
  | 'FLOATING_ORB'
  | 'AMBIENT_STREAM'
  | 'WHISPER_PILL';

export type NotificationPriority =
  | 'P0_CRITICAL'
  | 'P1_HIGH'
  | 'P2_NORMAL'
  | 'P3_LOW';

export type ViewportMode =
  | 'IMMERSIVE_STAGE'
  | 'SPLIT_PIVOT'
  | 'FLOATING_WIDGET'
  | 'AMBIENT_BACKGROUND';

export type GpuLoad =
  | 'NONE'
  | 'LOW'
  | 'MEDIUM'
  | 'HIGH'
  | 'EXTREME';

export type SafeZone =
  | 'TOP_LEFT'
  | 'TOP_RIGHT'
  | 'BOTTOM_LEFT'
  | 'BOTTOM_RIGHT'
  | 'CENTER'
  | 'SCREEN_EDGE_GLOW';

export type VoiceInteraction =
  | 'CONTINUOUS_CO_PILOT'
  | 'ON_DEMAND_ASSISTANT'
  | 'SILENT_OBSERVER';

export type FocusLockLevel = 0 | 1 | 2 | 3;

export interface AssistantRequirement {
  preferredMorphology: AssistantMorphology;
  fallbackMorphology: AssistantMorphology;
  allowedSafeZones: SafeZone[];
  voiceInteraction: VoiceInteraction;
}

export interface ContextManifest {
  contextId: string;
  viewportMode: ViewportMode;
  gpuLoad: GpuLoad;
  assistantRequirement: AssistantRequirement;
  focusLockLevel: FocusLockLevel;
}

export interface NotificationEvent {
  id: string;
  priority: NotificationPriority;
  titleKey: string;
  messageKey: string;
  sourceModule: string;
  timestampMs: number;
}

export type ArbitrationAction =
  | 'PREEMPTION_TOTAL'
  | 'SMART_PIP'
  | 'VOICE_INTERJECT'
  | 'MICRO_BADGE'
  | 'DEFERRAL'
  | 'SILENT_LOG';

export interface ArbitrationResult {
  action: ArbitrationAction;
  targetMorphology: AssistantMorphology;
  assignedSafeZone?: SafeZone;
  suspendPrimaryStage: boolean;
  targetLayer: 'Z0_Ambient' | 'Z1_PrimaryStage' | 'Z2_ContextualHud' | 'Z3_Assistant' | 'Z4_CriticalInterrupt';
  shouldDefer: boolean;
  reasonCode: string;
}

export const IDLE_CONTEXT_MANIFEST: ContextManifest = {
  contextId: 'app.nuxiva.idle',
  viewportMode: 'AMBIENT_BACKGROUND',
  gpuLoad: 'LOW',
  assistantRequirement: {
    preferredMorphology: 'CORE_HERO',
    fallbackMorphology: 'FLOATING_ORB',
    allowedSafeZones: ['CENTER'],
    voiceInteraction: 'CONTINUOUS_CO_PILOT',
  },
  focusLockLevel: 0,
};

export const CHESS_CONTEXT_MANIFEST: ContextManifest = {
  contextId: 'app.nuxiva.chess',
  viewportMode: 'IMMERSIVE_STAGE',
  gpuLoad: 'MEDIUM',
  assistantRequirement: {
    preferredMorphology: 'FLOATING_ORB',
    fallbackMorphology: 'AMBIENT_STREAM',
    allowedSafeZones: ['TOP_RIGHT', 'BOTTOM_RIGHT'],
    voiceInteraction: 'CONTINUOUS_CO_PILOT',
  },
  focusLockLevel: 2,
};

export const CAD3D_CONTEXT_MANIFEST: ContextManifest = {
  contextId: 'app.nuxiva.cad3d',
  viewportMode: 'IMMERSIVE_STAGE',
  gpuLoad: 'HIGH',
  assistantRequirement: {
    preferredMorphology: 'AMBIENT_STREAM',
    fallbackMorphology: 'AMBIENT_STREAM',
    allowedSafeZones: [],
    voiceInteraction: 'CONTINUOUS_CO_PILOT',
  },
  focusLockLevel: 3,
};
