export type InquiryScope =
  | 'architecture'
  | 'data_model'
  | 'security_policy'
  | 'payment_and_compliance'
  | 'user_experience'
  | 'integration_contract';

export type ResolutionSource =
  | 'autonomous_architect'
  | 'shared_contract'
  | 'escalate_to_user';

export interface EpistemicQuestionItem {
  id: string;
  scope: InquiryScope;
  question_key: string;
  default_answer_key: string;
  voi_bps: number;
  resolution: ResolutionSource;
  options_keys: string[];
  selected_option_key?: string;
}

export interface ForgedToolProofItem {
  tool_name: string;
  call_name: string;
  version: number;
  passed_cases: number;
  total_duration_ms: number;
  digest: string;
  status: 'proposed' | 'active' | 'quarantined' | 'revoked';
}

export interface CompiledShortcutItem {
  shortcut_id: string;
  intent: string;
  action_target: string;
  consolidated_hits: number;
  promoted_to_fast_path: boolean;
}

export interface AutonomyCognitionSnapshot {
  goal_key: string;
  confidence_bps: number;
  questions: EpistemicQuestionItem[];
  forged_tools: ForgedToolProofItem[];
  shortcuts: CompiledShortcutItem[];
}
