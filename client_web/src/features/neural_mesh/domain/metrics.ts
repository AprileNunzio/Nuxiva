import { MeshNeuron } from './types';

const STALE_AFTER_SECONDS = 15;

export interface MeshAggregate {
  readonly total: number;
  readonly online: number;
  readonly averageCpu: number | null;
  readonly ramUsedGb: number;
  readonly ramTotalGb: number;
  readonly gpuCount: number;
  readonly powerWatts: number | null;
  readonly byKind: Readonly<Record<MeshNeuron['kind'], number>>;
}

export function ratio(used: number | null, total: number | null): number | null {
  if (used === null || total === null || total <= 0) {
    return null;
  }
  return Math.min(1, Math.max(0, used / total));
}

export function cpuRatio(neuron: MeshNeuron): number | null {
  const value = neuron.telemetry.cpuPercent;
  return value === null ? null : value / 100;
}

export function isStale(neuron: MeshNeuron, nowMs: number): boolean {
  if (neuron.online !== null) {
    return !neuron.online;
  }
  const updated = neuron.telemetry.lastUpdated;
  if (updated === null) {
    return false;
  }
  return nowMs / 1000 - updated > STALE_AFTER_SECONDS;
}

export function synapseIntensity(neuron: MeshNeuron): number {
  const load = cpuRatio(neuron);
  return load === null ? 0.35 : 0.2 + load * 0.8;
}

export function aggregateMesh(neurons: readonly MeshNeuron[], nowMs: number): MeshAggregate {
  const byKind = { compute: 0, satellite: 0, micro: 0, mobile: 0 };
  let online = 0;
  let cpuSum = 0;
  let cpuSamples = 0;
  let ramUsedGb = 0;
  let ramTotalGb = 0;
  let gpuCount = 0;
  let powerWatts = 0;
  let powerSamples = 0;

  for (const neuron of neurons) {
    const t = neuron.telemetry;
    byKind[neuron.kind] += 1;
    online += isStale(neuron, nowMs) ? 0 : 1;
    if (t.cpuPercent !== null) {
      cpuSum += t.cpuPercent;
      cpuSamples += 1;
    }
    ramUsedGb += t.ramUsedGb ?? 0;
    ramTotalGb += t.ramTotalGb ?? 0;
    gpuCount += t.gpuName ? 1 : 0;
    if (t.powerWatts !== null) {
      powerWatts += t.powerWatts;
      powerSamples += 1;
    }
  }

  return {
    total: neurons.length,
    online,
    averageCpu: cpuSamples > 0 ? cpuSum / cpuSamples : null,
    ramUsedGb,
    ramTotalGb,
    gpuCount,
    powerWatts: powerSamples > 0 ? powerWatts : null,
    byKind,
  };
}

export function descendantIds(rootId: string, neurons: readonly MeshNeuron[]): Set<string> {
  const result = new Set<string>();
  const queue = [rootId];
  while (queue.length > 0) {
    const current = queue.shift() as string;
    for (const neuron of neurons) {
      if (neuron.parentId === current && !result.has(neuron.id)) {
        result.add(neuron.id);
        queue.push(neuron.id);
      }
    }
  }
  return result;
}
