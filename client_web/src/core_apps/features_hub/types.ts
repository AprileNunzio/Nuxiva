export * from '../shared/featureTypes';

export interface DisplaySettings {
  show_assistant_name: boolean;
  show_clock: boolean;
  show_date: boolean;
  show_thinking: boolean;
  show_dock: boolean;
  show_mic: boolean;
  show_telemetry_chips: boolean;
  show_presence: boolean;
  show_holo_avatar: boolean;
  show_desk_widgets: boolean;
  sound_effects: boolean;
}

export interface BackendSettings {
  ollama_url: string;
  active_llm_model: string;
  fast_llm_model: string;
  auto_shutdown_local_ollama: boolean;
  mesh_broadcast: boolean;
  mesh_state_sync: boolean;
  process_watchdog: boolean;
  verbose_telemetry: boolean;
}

export interface ScannedModel {
  name: string;
  size?: number;
  parameter_size?: string;
  quantization_level?: string;
  family?: string;
  modified_at?: string;
}
