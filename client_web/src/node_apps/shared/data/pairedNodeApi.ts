import { asRecord, asString, asStringList, requestJson } from './http';

export interface PairedHardware {
  readonly audioIn: readonly string[];
  readonly audioOut: readonly string[];
  readonly cameras: readonly string[];
  readonly usb: readonly string[];
  readonly bluetooth: boolean;
  readonly irCamera: boolean;
  readonly gpu: string | null;
  readonly os: string | null;
}

export interface PairedNode {
  readonly id: string;
  readonly online: boolean;
  readonly capabilities: readonly string[];
  readonly version: string | null;
  readonly hardware: PairedHardware | null;
}

function parseHardware(value: unknown): PairedHardware | null {
  if (typeof value !== 'object' || value === null) {
    return null;
  }
  const hw = asRecord(value);
  return {
    audioIn: asStringList(hw.audio_in),
    audioOut: asStringList(hw.audio_out),
    cameras: asStringList(hw.cameras),
    usb: asStringList(hw.usb),
    bluetooth: hw.bluetooth === true,
    irCamera: hw.ir_camera === true,
    gpu: asString(hw.gpu),
    os: asString(hw.os),
  };
}

export async function fetchPairedNode(nodeId: string, signal?: AbortSignal): Promise<PairedNode | null> {
  const payload = asRecord(await requestJson<unknown>('/api/nodes', { signal }));
  const nodes = Array.isArray(payload.nodes) ? payload.nodes : [];
  const raw = nodes.map(asRecord).find((node) => node.id === nodeId);
  if (!raw) {
    return null;
  }
  return {
    id: nodeId,
    online: raw.online === true,
    capabilities: asStringList(raw.capabilities),
    version: asString(raw.version, 40),
    hardware: parseHardware(raw.hardware),
  };
}
