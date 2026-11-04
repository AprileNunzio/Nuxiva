export interface HabitSuggestion {
  readonly id: string;
  readonly kind: string;
  readonly entity: string;
  readonly state: string;
  readonly text: string;
  readonly confidence: number;
  readonly support: number;
  readonly observed: number;
  readonly status: string;
  readonly automation?: { readonly name?: string };
}

export interface HabitAnomaly {
  readonly at: number;
  readonly entity: string;
  readonly text: string;
}

export interface HabitForesight {
  readonly entity: string;
  readonly state: string;
  readonly confidence: number;
  readonly reason: string;
  readonly until: number;
}

export interface HabitsOverview {
  readonly enabled: boolean;
  readonly threshold: number;
  readonly events: number;
  readonly mined: number;
  readonly suggestions: readonly HabitSuggestion[];
  readonly anomalies: readonly HabitAnomaly[];
  readonly foresight: readonly HabitForesight[];
  readonly foresight_hits: number;
}
