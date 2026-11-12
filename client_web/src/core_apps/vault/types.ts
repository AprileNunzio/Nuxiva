export interface VaultOverview {
  readonly enabled: boolean;
  readonly root: string;
  readonly files: readonly string[];
  readonly last_export: number;
  readonly imports: readonly unknown[];
  readonly today: string;
}
