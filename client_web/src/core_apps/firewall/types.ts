export interface FirewallPolicy {
  readonly mode: string;
  readonly allow_lan: boolean;
  readonly allow_ping: boolean;
  readonly auto_block: boolean;
  readonly auto_block_severity: string;
  readonly auto_block_minutes: number;
  readonly ai_analysis: boolean;
  readonly autonomy: string;
  readonly tarpit: boolean;
  readonly honeypot: boolean;
  readonly quarantine: boolean;
  readonly country_block: boolean;
  readonly country_threshold: number;
  readonly home_countries: readonly string[];
  readonly max_actions_per_hour: number;
  readonly max_block_minutes: number;
  readonly geo_updates: boolean;
}

export interface FirewallRule {
  readonly id: string;
  readonly action: string;
  readonly direction: string;
  readonly protocol: string;
  readonly sources: readonly string[];
  readonly destinations: readonly string[];
  readonly ports: readonly string[];
  readonly interface: string;
  readonly rate: string;
  readonly comment: string;
  readonly enabled: boolean;
  readonly priority: number;
  readonly expires: number;
}

export interface FirewallBlock {
  readonly address: string;
  readonly expires: number;
  readonly reason: string;
}

export interface FirewallAlert {
  readonly kind: string;
  readonly severity: string;
  readonly src: string;
  readonly dst: string;
  readonly count: number;
  readonly detail: string;
  readonly at: number;
}

export interface FirewallOverview {
  readonly policy: FirewallPolicy;
  readonly rules: readonly FirewallRule[];
  readonly blocks: readonly FirewallBlock[];
  readonly alerts: readonly FirewallAlert[];
  readonly status: { readonly ok: boolean | null; readonly error: string; readonly available: boolean; readonly confirm_by: number };
  readonly engine: { readonly connected: boolean };
}

export interface RuleDraft {
  readonly action: string;
  readonly direction: string;
  readonly protocol: string;
  readonly ports: readonly string[];
  readonly sources: readonly string[];
  readonly comment: string;
}

export interface DefenseIncident {
  readonly id: string;
  readonly kinds: readonly string[];
  readonly stage: string;
  readonly level: string;
  readonly country: string | null;
  readonly src: string;
  readonly targets: readonly string[];
}

export interface DefenseResponse {
  readonly key: string;
  readonly kind: string;
  readonly target: string;
  readonly expires: number;
  readonly auto: boolean;
  readonly reason: string;
}

export interface GeoStatus {
  readonly loaded: boolean;
  readonly rows: number;
  readonly updated: number;
  readonly month: string;
  readonly attribution: string;
}

export interface DefenseState {
  readonly posture: string;
  readonly incidents: readonly DefenseIncident[];
  readonly responses: readonly DefenseResponse[];
  readonly geo: GeoStatus;
  readonly journal_ok: boolean;
}

export interface TrustedDevice {
  readonly address: string;
  readonly label: string;
  readonly since: number;
  readonly by: string;
  readonly online: boolean;
}

export interface TrustRequest {
  readonly id: string;
  readonly code: string;
  readonly addresses: readonly string[];
  readonly label: string;
  readonly risks: readonly string[];
  readonly expires: number;
}

export interface JournalEntry {
  readonly at: number;
  readonly action: string;
  readonly kind: string;
  readonly target: string;
  readonly by: string;
  readonly ok: boolean;
  readonly detail?: string;
  readonly hash: string;
}

export interface JournalState {
  readonly entries: readonly JournalEntry[];
  readonly intact: boolean;
}
