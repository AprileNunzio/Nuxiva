export type OptionCategory =
  | 'multimedia'
  | 'security'
  | 'ai_voice'
  | 'display'
  | 'privacy';

export interface SystemSwitchOption {
  id: string;
  category: OptionCategory;
  enabled: boolean;
  defaultEnabled: boolean;
  titleKey: string;
  descriptionKey: string;
  tags: string[];
}
