export interface SettingOption {
  readonly value: string;
  readonly label: string;
}

export interface FeatureSetting {
  readonly key: string;
  readonly label: string;
  readonly type: string;
  readonly default?: string;
  readonly options?: readonly (SettingOption | string)[];
  readonly button?: string;
}

export interface FeatureRow {
  readonly id: string;
  readonly name: string;
  readonly icon: string;
  readonly category: string;
  readonly description: string;
  readonly capabilities: readonly string[];
  readonly settings: readonly FeatureSetting[];
  readonly values: Readonly<Record<string, string>>;
  readonly state: { readonly enabled: boolean; readonly mode: string; readonly reason: string };
  readonly pinned: boolean;
  readonly source: string;
  readonly new: boolean;
}

export interface FeaturesOverview {
  readonly features: readonly FeatureRow[];
  readonly categories: Readonly<Record<string, string>>;
  readonly errors: readonly unknown[];
}
