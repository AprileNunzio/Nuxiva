import { MeshNeuron, MeshSnapshot, NeuronKind, NeuronTelemetry } from '../domain/types';
import { cleanBoolean, cleanId, cleanIp, cleanNumber, cleanText, isRecord } from './sanitize';

const MAX_NEURONS = 512;
const MAX_EPOCH_SECONDS = 1e11;

const KIND_ALIASES: Readonly<Record<string, NeuronKind>> = {
  compute: 'compute',
  core: 'compute',
  satellite: 'satellite',
  micro: 'micro',
  mobile: 'mobile',
};

export class TopologyParseError extends Error {
  constructor(readonly code: string) {
    super(code);
    this.name = 'TopologyParseError';
  }
}

function parseKind(value: unknown): NeuronKind {
  const key = typeof value === 'string' ? value.trim().toLowerCase() : '';
  return KIND_ALIASES[key] ?? 'satellite';
}

function parseTelemetry(value: unknown): NeuronTelemetry {
  const t = isRecord(value) ? value : {};
  return {
    cpuName: cleanText(t.cpu_name, 96),
    cpuCores: cleanNumber(t.cpu_cores, 0, 4096),
    cpuPercent: cleanNumber(t.cpu_percent, 0, 100),
    ramUsedGb: cleanNumber(t.ram_used_gb, 0, 1e5),
    ramTotalGb: cleanNumber(t.ram_total_gb, 0, 1e5),
    gpuName: cleanText(t.gpu_name, 96),
    vramUsedGb: cleanNumber(t.vram_used_gb, 0, 1e4),
    vramTotalGb: cleanNumber(t.vram_total_gb, 0, 1e4),
    activeModel: cleanText(t.active_model, 96),
    os: cleanText(t.os, 64),
    powerWatts: cleanNumber(t.power_watts, 0, 1e5),
    tempC: cleanNumber(t.temp_c, -60, 200),
    pingMs: cleanNumber(t.ping_ms, 0, 1e5),
    txKbps: cleanNumber(t.tx_kbps, 0, 1e9),
    rxKbps: cleanNumber(t.rx_kbps, 0, 1e9),
    lastUpdated: cleanNumber(t.last_updated, 0, MAX_EPOCH_SECONDS),
    uptimeSeconds: cleanNumber(t.uptime_s, 0, 1e10),
  };
}

function parseNeuron(value: unknown): MeshNeuron | null {
  if (!isRecord(value)) {
    return null;
  }
  const id = cleanId(value.id);
  if (!id) {
    return null;
  }
  return {
    id,
    name: cleanText(value.name, 64) ?? id,
    kind: parseKind(value.type),
    tier: cleanText(value.tier, 64),
    ip: cleanIp(value.ip),
    parentId: cleanId(value.parent_id),
    isRemoteVpn: cleanBoolean(value.is_remote_vpn),
    online: typeof value.online === 'boolean' ? value.online : null,
    room: cleanText(value.room, 60),
    paired: value.source === 'paired',
    telemetry: parseTelemetry(value.telemetry),
  };
}

function detachOrphans(neurons: MeshNeuron[]): MeshNeuron[] {
  const ids = new Set(neurons.map((n) => n.id));
  return neurons.map((n) =>
    n.parentId !== null && (n.parentId === n.id || !ids.has(n.parentId)) ? { ...n, parentId: null } : n,
  );
}

function breakCycles(neurons: MeshNeuron[]): MeshNeuron[] {
  const byId = new Map(neurons.map((n) => [n.id, n]));
  return neurons.map((neuron) => {
    const visited = new Set<string>([neuron.id]);
    let cursor = neuron.parentId;
    while (cursor !== null) {
      if (visited.has(cursor)) {
        return { ...neuron, parentId: null };
      }
      visited.add(cursor);
      cursor = byId.get(cursor)?.parentId ?? null;
    }
    return neuron;
  });
}

export function parseTopology(payload: unknown, receivedAt: number): MeshSnapshot {
  if (!isRecord(payload) || !Array.isArray(payload.nodes)) {
    throw new TopologyParseError('topology_payload_invalid');
  }
  const seen = new Set<string>();
  const neurons: MeshNeuron[] = [];
  for (const raw of payload.nodes.slice(0, MAX_NEURONS)) {
    const neuron = parseNeuron(raw);
    if (neuron && !seen.has(neuron.id)) {
      seen.add(neuron.id);
      neurons.push(neuron);
    }
  }
  return {
    neurons: breakCycles(detachOrphans(neurons)),
    receivedAt,
    serverTimestamp: cleanNumber(payload.timestamp, 0, MAX_EPOCH_SECONDS),
  };
}
