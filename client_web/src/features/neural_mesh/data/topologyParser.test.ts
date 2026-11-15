import { describe, expect, it } from 'vitest';
import { parseTopology } from './topologyParser';

const phone = {
  id: 'pixel',
  name: 'Pixel',
  type: 'mobile',
  online: true,
  source: 'paired',
  telemetry: { cpu_percent: 21, ram_used_gb: 4, ram_total_gb: 8, power_watts: 4.5, ping_ms: 38, gpu_percent: 12, battery_percent: 77, charging: false },
};

describe('parseTopology', () => {
  it('keeps power, latency, gpu and battery', () => {
    const snap = parseTopology({ nodes: [phone], timestamp: 1 }, 0);
    const t = snap.neurons[0].telemetry;
    expect(t.powerWatts).toBe(4.5);
    expect(t.pingMs).toBe(38);
    expect(t.gpuPercent).toBe(12);
    expect(t.batteryPercent).toBe(77);
    expect(t.charging).toBe(false);
  });

  it('accepts only nearest ids that exist', () => {
    const ok = parseTopology({ nodes: [phone], nearest: { node_id: 'pixel', confidence: 0.7 } }, 0);
    expect(ok.nearest).toEqual({ nodeId: 'pixel', confidence: 0.7, ambiguous: false });
    const bad = parseTopology({ nodes: [phone], nearest: { node_id: 'ghost', confidence: 2, ambiguous: true } }, 0);
    expect(bad.nearest.nodeId).toBeNull();
    expect(bad.nearest.confidence).toBe(1);
    expect(bad.nearest.ambiguous).toBe(true);
  });

  it('survives a missing nearest block', () => {
    expect(parseTopology({ nodes: [phone] }, 0).nearest.nodeId).toBeNull();
  });

  it('clamps out of range values', () => {
    const t = parseTopology({ nodes: [{ ...phone, telemetry: { gpu_percent: 900, battery_percent: -4 } }] }, 0).neurons[0].telemetry;
    expect(t.gpuPercent).toBe(100);
    expect(t.batteryPercent).toBe(0);
  });
});
