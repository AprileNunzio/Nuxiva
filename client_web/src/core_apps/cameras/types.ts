export interface CameraRow {
  readonly id: string;
  readonly name: string;
  readonly kind: string;
  readonly node: string;
  readonly retention_min: number;
  readonly enabled: boolean;
  readonly record: boolean;
  readonly consent: boolean;
  readonly recording: boolean;
  readonly has_url: boolean;
}

export interface CamerasOverview {
  readonly cameras: readonly CameraRow[];
  readonly kinds: readonly string[];
  readonly retentions: readonly number[];
}

export interface CameraSource {
  readonly id: string;
  readonly name: string;
  readonly kind: string;
  readonly room: string;
}

export interface CameraDraft {
  readonly name: string;
  readonly kind: string;
  readonly url: string;
  readonly retention_min: number;
}
