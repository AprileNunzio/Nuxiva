export interface Traits {
  readonly speed: number;
  readonly quality: number;
  readonly privacy: number;
  readonly saving: number;
}

export interface Algorithm {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly traits: Traits;
  readonly default: boolean;
  readonly available: boolean;
}

export interface FlowNode {
  readonly id: string;
  readonly label: string;
  readonly glyph: string;
  readonly description: string;
  readonly locked: boolean;
  readonly editable: boolean;
  readonly algorithms: readonly Algorithm[];
}

export interface FlowTemplate {
  readonly name: string;
  readonly hint: string;
  readonly picks: Readonly<Record<string, string>>;
}

export interface FlowVersion {
  readonly version: number;
  readonly author: string;
  readonly at: number;
  readonly note: string;
  readonly auto: boolean;
}

export interface FlowStep {
  readonly node: string;
  readonly algorithm: string;
  readonly seconds: number;
}

export interface FlowStudio {
  readonly nodes: readonly FlowNode[];
  readonly templates: Readonly<Record<string, FlowTemplate>>;
  readonly versions: readonly FlowVersion[];
  readonly draft: { readonly picks: Readonly<Record<string, string>>; readonly template: string };
  readonly current: Readonly<Record<string, string>>;
  readonly pending: Readonly<Record<string, string>>;
  readonly traits: { readonly draft: Traits; readonly current: Traits };
  readonly estimate: readonly FlowStep[];
}
