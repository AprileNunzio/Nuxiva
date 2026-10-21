export type ComponentHealth = 'ok' | 'suspect' | 'fault' | 'unknown';

export interface LocalizedMessage {
  readonly key?: string | null;
  readonly params?: Record<string, string>;
  readonly text?: string | null;
}

export interface PinSpec {
  readonly number: string;
  readonly name: string;
  readonly electrical_type: string;
}

export interface ComponentSpec {
  readonly ref: string;
  readonly value: string;
  readonly category: string;
  readonly package: string;
  readonly description: string;
  readonly pins: readonly PinSpec[];
}

export interface PinRef {
  readonly ref: string;
  readonly pin: string;
}

export interface NetSpec {
  readonly name: string;
  readonly connections: readonly PinRef[];
}

export interface CircuitSpec {
  readonly name: string;
  readonly description: string;
  readonly components: readonly ComponentSpec[];
  readonly nets: readonly NetSpec[];
}

export interface ARComponentPopup {
  readonly track_id: number;
  readonly key: string;
  readonly label: string;
  readonly value: string;
  readonly category: string;
  readonly bbox: readonly [number, number, number, number];
  readonly health: ComponentHealth;
  readonly notes: string;
  readonly expected_voltages: Record<string, number>;
  readonly taught: boolean;
}

export interface BoardDossier {
  readonly title: string;
  readonly board_kind: string;
  readonly summary: string;
  readonly characteristics: readonly string[];
  readonly anomalies: readonly LocalizedMessage[];
  readonly component_count: number;
}

export interface AgentNote {
  readonly agent_id: string;
  readonly message: LocalizedMessage;
}

export interface WorkbenchSession {
  readonly vision_model?: string;
  readonly session_id: string;
  readonly project_id: string;
  readonly camera_id: string;
  readonly camera_name: string;
  readonly language: string;
  readonly created_at: number;
  readonly updated_at: number;
  readonly scene_state: string;
  readonly frame_count: number;
  readonly dossier: BoardDossier;
  readonly popups: readonly ARComponentPopup[];
  readonly circuit: CircuitSpec;
  readonly expected_voltages: Record<string, number>;
  readonly advice: readonly LocalizedMessage[];
  readonly notes: readonly AgentNote[];
  readonly aliases: Record<string, string>;
  readonly taught_values: Record<string, string>;
}

export interface CameraSourceItem {
  readonly id: string;
  readonly name: string;
  readonly kind: string;
}

export interface ProjectSummaryItem {
  readonly project_id: string;
  readonly name: string;
  readonly goal: string;
  readonly assigned_agents: readonly string[];
}

export interface WorkbenchLaunchItem {
  readonly launch_id: string;
  readonly project_id: string;
  readonly created_at: number;
}
