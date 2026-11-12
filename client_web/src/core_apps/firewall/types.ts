export interface FirewallPolicy {
  readonly mode: string;
  readonly allow_lan: boolean;
  readonly allow_ping: boolean;
  readonly auto_block: boolean;
  readonly auto_block_severity: string;
  readonly auto_block_minutes: number;
  readonly ai_analysis: boolean;
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
