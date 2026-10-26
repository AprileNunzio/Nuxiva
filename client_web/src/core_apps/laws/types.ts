export interface FixedLaw {
  readonly id: string;
  readonly n: number;
  readonly title: string;
  readonly text: string;
}

export interface CustomLaw {
  readonly id: string;
  readonly text: string;
  readonly created: number;
  readonly origin: string;
}

export interface LawsOverview {
  readonly fixed: readonly FixedLaw[];
  readonly custom: readonly CustomLaw[];
  readonly max: number;
}
