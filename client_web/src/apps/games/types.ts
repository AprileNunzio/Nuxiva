export interface GameCommand {
  command_id: string;
  name_key: string;
  description_key: string;
  input_types: string[];
  voice_triggers: string[];
  parameters: Record<string, any>;
  requires_confirmation: boolean;
  is_async: boolean;
}

export interface GameCapability {
  capability_id: string;
  category: string;
  name_key: string;
  description_key: string;
  enabled: boolean;
  metadata?: Record<string, any>;
}

export interface GameItem {
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

export type GameFilterStatus = 'all' | 'active' | 'disabled';
