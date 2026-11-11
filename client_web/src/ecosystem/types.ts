export type EcosystemKind = 'agent' | 'skill' | 'plugin' | 'brain' | 'engine';

export interface EcosystemPlacement {
  desktop?: boolean;
  taskbar?: {
    pinned?: boolean;
    tray?: boolean;
    tray_order?: number;
  };
  control_panel?: {
    show?: boolean;
    category?: string;
    subapp_of?: string;
  };
}

export interface EcosystemOption {
  id: string;
  type: 'boolean' | 'string' | 'number' | 'range' | 'select';
  default: string | number | boolean;
  min?: number;
  max?: number;
  step?: number;
  options?: Array<{ value: string; label_key: string }>;
  label_key: string;
  desc_key: string;
}

export interface EcosystemManifest {
  id: string;
  name: string;
  version: string;
  kind: EcosystemKind;
  author: string;
  role?: string;
  family?: string;
  scope: string;
  placement?: EcosystemPlacement;
  capabilities: string[];
  options: EcosystemOption[];
}
