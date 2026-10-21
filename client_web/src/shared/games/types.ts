export type CommandInputType = 'voice' | 'ui_action' | 'shortcut' | 'api_call';

export type CapabilityCategory = 'rendering' | 'audio' | 'ai' | 'input' | 'network' | 'storage' | 'physics';

export interface GameCommand {
  command_id: string;
  name_key: string;
  description_key: string;
  input_types: CommandInputType[];
  voice_triggers: string[];
  parameters: Record<string, any>;
  requires_confirmation: boolean;
  is_async: boolean;
}

export interface GameCapability {
  capability_id: string;
  category: CapabilityCategory;
  name_key: string;
  description_key: string;
  enabled: boolean;
  metadata?: Record<string, any>;
}

export interface GameManifest {
  game_id: string;
  name: string;
  version: string;
  category: string;
  description: string;
  icon: string;
  entrypoint: string;
  tech_stack: string[];
  commands: GameCommand[];
  capabilities: GameCapability[];
  directory_path: string;
  is_active: boolean;
  metadata: Record<string, any>;
}

export interface CommandExecutionPayload {
  command_id: string;
  parameters?: Record<string, any>;
  session_id?: string;
}

export interface CommandExecutionOutcome {
  success: boolean;
  command_id: string;
  result_data: Record<string, any>;
  feedback_speech_key?: string;
  error_message?: string;
}
