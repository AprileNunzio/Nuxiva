export type Tier = 'continuous' | 'event' | 'pinned';

export interface RecordingCamera {
  camera: string;
  name: string;
  room: string;
  segments: number;
  bytes: number;
  first_ms: number;
  last_ms: number;
  audio_segments: number;
}

export interface SegmentRow {
  id: string;
  start_ms: number;
  duration_ms: number;
  tier: Tier;
  audio: boolean;
  video: boolean;
  bytes: number;
}

export interface Span {
  start_ms: number;
  end_ms: number;
  segments: number;
  audio: boolean;
}

export interface Marker {
  at_ms: number;
  camera: string;
  kind: string;
  id: string;
  label: string;
  score: number;
}

export interface Timeline {
  camera: string;
  from_ms: number;
  to_ms: number;
  spans: Span[];
  markers: Marker[];
  segments: SegmentRow[];
}

export interface SeekResult {
  segment: SegmentRow & { camera: string };
  offset_ms: number;
  gap_ms: number;
}

export interface JumpResult {
  marker: Marker;
  seek: SeekResult | null;
}

export interface StorageStats {
  quota_bytes: number;
  vault_used_bytes: number;
  quota_used_percent: number;
}
