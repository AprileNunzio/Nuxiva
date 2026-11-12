export interface ShareFolder {
  readonly kind: string;
  readonly name: string;
  readonly description: string;
  readonly count: number;
  readonly latest: readonly string[];
}

export interface ShareSession {
  readonly pid: number;
  readonly user: string;
  readonly machine: string;
  readonly address: string;
  readonly protocol: string;
  readonly encryption: string;
  readonly signing: string;
}

export interface ShareSettings {
  readonly readonly: boolean;
  readonly networks: readonly string[];
  readonly recycle: boolean;
  readonly discovery: boolean;
  readonly upload_mb: number;
  readonly protocol: string;
  readonly encrypt: string;
}

export interface SharesOverview {
  readonly active: string;
  readonly ip: string;
  readonly windows: string;
  readonly unc: string;
  readonly user: string;
  readonly password: string;
  readonly folders: readonly ShareFolder[];
  readonly root: string;
  readonly settings: ShareSettings;
  readonly sessions: readonly ShareSession[];
}
