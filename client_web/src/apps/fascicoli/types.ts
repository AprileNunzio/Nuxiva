export interface FascicoloItem {
  readonly rel: string;
  readonly id: string;
  readonly level: string;
  readonly agents: string;
  readonly created: string;
  readonly lang: string;
  readonly request: string;
  readonly closed: boolean;
  readonly checked: boolean;
}

export interface FascicoloSection {
  readonly anchor: string;
  readonly heading: string;
  readonly body: string;
}

export interface FascicoloDoc {
  readonly front: readonly (readonly [string, string])[];
  readonly title: string;
  readonly sections: readonly FascicoloSection[];
}

export interface FascicoloProblem {
  readonly at: string;
  readonly code: string;
}

export interface FascicoloReport {
  readonly ok: boolean;
  readonly level: string;
  readonly complete: boolean;
  readonly files: readonly string[];
  readonly problems: readonly FascicoloProblem[];
}

export interface FascicoloDetail {
  readonly rel: string;
  readonly report: FascicoloReport;
  readonly files: Readonly<Record<string, FascicoloDoc>>;
}
