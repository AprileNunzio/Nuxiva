export interface StudySettings {
  readonly enabled: boolean;
  readonly idle_minutes: number;
  readonly max_cpu: number;
  readonly daily_minutes: number;
  readonly auto_discover: boolean;
  readonly auto_accept: boolean;
  readonly web_sources: boolean;
  readonly use_in_answers: boolean;
}

export interface StudyLevelDetail {
  readonly level: number;
  readonly name: string;
  readonly progress: number;
  readonly lessons: number;
  readonly done: number;
}

export interface StudyTopic {
  readonly id: string;
  readonly name: string;
  readonly source: string;
  readonly status: string;
  readonly priority: number;
  readonly target_level: number;
  readonly level: number;
  readonly level_name: string;
  readonly progress: number;
  readonly cells: number;
  readonly due_reviews: number;
  readonly levels_detail: readonly StudyLevelDetail[];
}

export interface StudyMention {
  readonly name: string;
  readonly count?: number;
  readonly [key: string]: unknown;
}

export interface StudyOverview {
  readonly settings: StudySettings;
  readonly status: { readonly state: string; readonly detail: string; readonly topic: string; readonly level: string; readonly cells: number; readonly today_minutes: number };
  readonly topics: readonly StudyTopic[];
  readonly mentions: readonly (StudyMention & { readonly key?: string })[];
  readonly stats: { readonly seconds_today: number; readonly seconds_total: number; readonly lessons: number; readonly reviews: number; readonly exams: number };
  readonly memory: { readonly cells: number };
  readonly levels: Readonly<Record<string, string>>;
}

export interface StudyHit {
  readonly text: string;
  readonly score: number;
  readonly topic_name: string;
  readonly level: string;
}
