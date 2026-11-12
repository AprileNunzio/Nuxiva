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
  readonly help?: string;
  readonly see?: string;
  readonly see_name?: string;
}

export interface FeatureGuide {
  readonly title: string;
  readonly steps: readonly string[];
  readonly links: readonly { readonly label: string; readonly url: string }[];
  readonly note: string;
  readonly items_title?: string;
  readonly items?: readonly { readonly label: string; readonly detail: string; readonly url: string }[];
  readonly copy?: readonly { readonly label: string; readonly text: string }[];
}

export interface FeatureRow {
  readonly id: string;
  readonly name: string;
  readonly icon: string;
  readonly icon_url?: string;
  readonly category: string;
  readonly description: string;
  readonly capabilities: readonly string[];
  readonly settings: readonly FeatureSetting[];
  readonly guide?: FeatureGuide | null;
  readonly values: Readonly<Record<string, string>>;
  readonly state: { readonly enabled: boolean; readonly mode: string; readonly reason: string };
  readonly pinned: boolean;
  readonly source: string;
  readonly new: boolean;
  readonly surface?: 'hub' | 'settings' | 'hidden';
}

export interface FeaturesOverview {
  readonly features: readonly FeatureRow[];
  readonly categories: Readonly<Record<string, string>>;
  readonly errors: readonly unknown[];
}
