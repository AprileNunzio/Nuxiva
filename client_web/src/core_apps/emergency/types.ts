export interface RedAlertStatus {
  readonly enabled: boolean;
  readonly active: boolean;
  readonly message: string;
  readonly seconds: number;
}
