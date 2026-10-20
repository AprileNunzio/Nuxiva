import { bendControl, clamp, moveToward, onEllipse } from './geometry';
import { synapseIntensity } from './metrics';
import { MeshLayout, MeshNeuron, NEURON_KINDS, PlacedNeuron, Point, SynapsePath } from './types';

export interface LayoutInput {
  readonly width: number;
  readonly height: number;
  readonly insetRight: number;
  readonly neurons: readonly MeshNeuron[];
}

interface LayoutContext {
  readonly center: Point;
  readonly rx: number;
  readonly ry: number;
  readonly firstRing: number;
  readonly ringStep: number;
  readonly minSeparation: number;
  readonly fillRatio: number;
  readonly groups: Map<string | null, MeshNeuron[]>;
  readonly placed: PlacedNeuron[];
}

const OUTER_RING = 0.96;

function compareNeurons(a: MeshNeuron, b: MeshNeuron): number {
  const kindOrder = NEURON_KINDS.indexOf(a.kind) - NEURON_KINDS.indexOf(b.kind);
  return kindOrder !== 0 ? kindOrder : a.name.localeCompare(b.name) || a.id.localeCompare(b.id);
}

function groupByParent(neurons: readonly MeshNeuron[]): Map<string | null, MeshNeuron[]> {
  const groups = new Map<string | null, MeshNeuron[]>();
  for (const neuron of neurons) {
    const bucket = groups.get(neuron.parentId) ?? [];
    bucket.push(neuron);
    groups.set(neuron.parentId, bucket);
  }
  groups.forEach((bucket) => bucket.sort(compareNeurons));
  return groups;
}

function subtreeWeight(id: string, groups: Map<string | null, MeshNeuron[]>): number {
  const children = groups.get(id) ?? [];
  return Math.max(1, children.reduce((sum, child) => sum + subtreeWeight(child.id, groups), 0));
}

function subtreeDepth(id: string, groups: Map<string | null, MeshNeuron[]>): number {
  const children = groups.get(id) ?? [];
  return 1 + children.reduce((max, child) => Math.max(max, subtreeDepth(child.id, groups)), 0);
}

function placeBranch(ctx: LayoutContext, neuron: MeshNeuron, angle: number, sector: number, depth: number): void {
  const fraction = Math.min(OUTER_RING, ctx.firstRing + (depth - 1) * ctx.ringStep);
  ctx.placed.push({ neuron, position: onEllipse(ctx.center, ctx.rx, ctx.ry, angle, fraction), depth });
  const children = ctx.groups.get(neuron.id) ?? [];
  if (children.length === 0) {
    return;
  }
  const childFraction = Math.min(OUTER_RING, ctx.firstRing + depth * ctx.ringStep);
  const ringRadius = Math.max(1, childFraction * Math.sqrt(ctx.rx * ctx.ry));
  const needed = (children.length * ctx.minSeparation) / ringRadius;
  const spread = Math.min(sector * 0.9, Math.PI * 1.6, Math.max(needed, sector * ctx.fillRatio));
  const weights = children.map((child) => subtreeWeight(child.id, ctx.groups));
  const total = weights.reduce((sum, w) => sum + w, 0);
  let cursor = angle - spread / 2;
  children.forEach((child, index) => {
    const share = (spread * weights[index]) / total;
    placeBranch(ctx, child, cursor + share / 2, share, depth + 1);
    cursor += share;
  });
}

function buildSynapses(
  placed: readonly PlacedNeuron[],
  center: Point,
  coreRadius: number,
  neuronRadius: number,
): SynapsePath[] {
  const byId = new Map(placed.map((p) => [p.neuron.id, p]));
  return placed.map((entry, index) => {
    const parent = entry.neuron.parentId ? byId.get(entry.neuron.parentId) : undefined;
    const origin = parent ? parent.position : center;
    const originRadius = parent ? neuronRadius * 1.05 : coreRadius * 0.92;
    const from = moveToward(origin, entry.position, originRadius);
    const to = moveToward(entry.position, origin, neuronRadius * 1.05);
    const bend = (parent ? 0.18 : 0.1) * (index % 2 === 0 ? 1 : -1);
    return {
      id: `${parent ? parent.neuron.id : 'core'}>${entry.neuron.id}`,
      sourceId: parent ? parent.neuron.id : null,
      targetId: entry.neuron.id,
      from,
      control: bendControl(from, to, bend),
      to,
      intensity: synapseIntensity(entry.neuron),
      kind: entry.neuron.kind,
    };
  });
}

export function computeMeshLayout({ width, height, insetRight, neurons }: LayoutInput): MeshLayout {
  const usableWidth = Math.max(0, width - insetRight);
  const compact = usableWidth < 640;
  const center = { x: usableWidth / 2, y: height / 2 };
  const span = Math.max(1, Math.min(usableWidth, height));
  const coreRadius = clamp(span * (compact ? 0.12 : 0.1), 38, 96);
  const neuronRadius = clamp(span * 0.04, 18, 30);
  const margin = neuronRadius * 2.6;
  const rx = Math.max(coreRadius * 2, usableWidth / 2 - margin);
  const ry = Math.max(coreRadius * 2, height / 2 - margin);
  const groups = groupByParent(neurons);
  const roots = groups.get(null) ?? [];
  const maxDepth = roots.reduce((max, root) => Math.max(max, subtreeDepth(root.id, groups)), 1);
  const firstRing = clamp((coreRadius + neuronRadius * 2.6) / Math.sqrt(rx * ry), 0.42, 0.74);
  const ringStep = maxDepth > 1 ? (OUTER_RING - firstRing) / (maxDepth - 1) : 0;
  const placed: PlacedNeuron[] = [];
  const ctx: LayoutContext = {
    center,
    rx,
    ry,
    firstRing,
    ringStep,
    minSeparation: Math.max(neuronRadius * 4.4, compact ? 84 : 120),
    fillRatio: compact ? 0.85 : 0.5,
    groups,
    placed,
  };

  const weights = roots.map((root) => subtreeWeight(root.id, groups));
  const total = weights.reduce((sum, w) => sum + w, 0) || 1;
  const baseAngle = usableWidth >= height ? Math.PI : -Math.PI / 2;
  let cursor = baseAngle - (Math.PI * 2 * (weights[0] ?? 1)) / total / 2;
  roots.forEach((root, index) => {
    const sector = (Math.PI * 2 * weights[index]) / total;
    placeBranch(ctx, root, cursor + sector / 2, sector, 1);
    cursor += sector;
  });

  return {
    center,
    coreRadius,
    neuronRadius,
    compact,
    placed,
    synapses: buildSynapses(placed, center, coreRadius, neuronRadius),
  };
}
