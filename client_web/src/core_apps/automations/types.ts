export interface Automation {
  readonly id: string;
  readonly name: string;
  readonly description?: string;
  readonly enabled: boolean;
  readonly runs?: number;
  readonly last_run?: number;
  readonly last_status?: string;
  readonly last_error?: string;
  readonly origin?: string;
}

export interface AutomationRun {
  readonly id: string;
  readonly automation: string;
  readonly name: string;
  readonly status: string;
  readonly started: number;
  readonly ended: number | null;
  readonly error: string;
  readonly steps: number;
  readonly ms: number;
}

export interface AutomationsOverview {
  readonly enabled: boolean;
  readonly status: string;
  readonly automations: readonly Automation[];
  readonly active: readonly AutomationRun[];
  readonly recent: readonly AutomationRun[];
  readonly waiting: readonly { readonly run: string; readonly name: string }[];
}

export interface AutomationTemplate {
  readonly index: number;
  readonly name: string;
  readonly description: string;
  readonly tags: readonly string[];
}

export interface GeneratedAutomation {
  readonly automation: Readonly<Record<string, unknown>>;
  readonly errors: readonly unknown[];
}
