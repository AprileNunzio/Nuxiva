export type NeuronKind = 'compute' | 'satellite' | 'micro' | 'mobile';

export const NEURON_KINDS: readonly NeuronKind[] = ['compute', 'satellite', 'micro', 'mobile'];

export const VIRTUAL_CORE_ID = 'virtual-core';

export type StreamKind = 'audio_pcm' | 'rtsp_video' | 'sensor_telemetry';

export const STREAM_KINDS: readonly StreamKind[] = ['audio_pcm', 'rtsp_video', 'sensor_telemetry'];

export type StreamState = 'connecting' | 'live' | 'reconnecting' | 'offline';

export interface NeuronTelemetry {
  readonly cpuName: string | null;
  readonly cpuCores: number | null;
  readonly cpuPercent: number | null;
  readonly ramUsedGb: number | null;
  readonly ramTotalGb: number | null;
  readonly gpuName: string | null;
  readonly vramUsedGb: number | null;
  readonly vramTotalGb: number | null;
  readonly activeModel: string | null;
  readonly os: string | null;
  readonly powerWatts: number | null;
  readonly tempC: number | null;
  readonly pingMs: number | null;
  readonly txKbps: number | null;
  readonly rxKbps: number | null;
  readonly lastUpdated: number | null;
  readonly uptimeSeconds: number | null;
}

export interface MeshNeuron {
  readonly id: string;
  readonly name: string;
  readonly kind: NeuronKind;
  readonly tier: string | null;
  readonly ip: string | null;
  readonly parentId: string | null;
  readonly isRemoteVpn: boolean;
  readonly online: boolean | null;
  readonly room: string | null;
  readonly paired: boolean;
  readonly telemetry: NeuronTelemetry;
}

export interface MeshSnapshot {
  readonly neurons: readonly MeshNeuron[];
  readonly receivedAt: number;
  readonly serverTimestamp: number | null;
}

export interface Point {
  readonly x: number;
  readonly y: number;
}

export interface PlacedNeuron {
  readonly neuron: MeshNeuron;
  readonly position: Point;
  readonly depth: number;
}

export interface SynapsePath {
  readonly id: string;
  readonly sourceId: string | null;
  readonly targetId: string;
  readonly from: Point;
  readonly control: Point;
  readonly to: Point;
  readonly intensity: number;
  readonly kind: NeuronKind;
}

export interface MeshLayout {
  readonly center: Point;
  readonly coreRadius: number;
  readonly neuronRadius: number;
  readonly compact: boolean;
  readonly placed: readonly PlacedNeuron[];
  readonly synapses: readonly SynapsePath[];
}

export type MeshSelection = { readonly type: 'core' } | { readonly type: 'neuron'; readonly id: string };
