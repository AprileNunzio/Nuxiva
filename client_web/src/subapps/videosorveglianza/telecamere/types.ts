export interface CameraRow {
  readonly id: string;
  readonly name: string;
  readonly kind: string;
  readonly node?: string;
  readonly retention_min?: number;
  readonly enabled: boolean;
  readonly record?: boolean;
  readonly consent?: boolean;
  readonly recording?: boolean;
  readonly has_url?: boolean;
}

export interface CameraSource {
  readonly id: string;
  readonly name: string;
  readonly kind: string;
  readonly main?: boolean;
  readonly ir?: boolean;
  readonly rotate?: number;
  readonly mirror?: boolean;
  readonly room?: string;
  readonly stream?: boolean;
  readonly client_transform?: boolean;
}

export interface CamerasOverview {
  readonly cameras: readonly CameraRow[];
  readonly kinds: readonly string[];
  readonly retentions: readonly number[];
}

export interface CameraDraft {
  readonly name: string;
  readonly kind: string;
  readonly url: string;
  readonly retention_min: number;
}
