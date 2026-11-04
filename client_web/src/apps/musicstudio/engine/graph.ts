import { buildEffect, type Fx } from './effects';
import type { Effect, Project, Track } from '../types';

export interface TrackNode {
  readonly input: GainNode;
  readonly gain: GainNode;
  readonly pan: StereoPannerNode;
  readonly meter: AnalyserNode;
  fx: Fx[];
  fxKey: string;
}

export interface MasterNode {
  readonly input: GainNode;
  readonly gain: GainNode;
  readonly meter: AnalyserNode;
  fx: Fx[];
  fxKey: string;
}

const beatSeconds = (project: Project) => 60 / project.tempo;

const chainKey = (effects: readonly Effect[]) => effects.filter((e) => e.on).map((e) => `${e.id}:${e.type}`).join('|');

const rewire = (head: AudioNode, tail: AudioNode, fx: readonly Fx[]) => {
  head.disconnect();
  let node: AudioNode = head;
  for (const f of fx) {
    node.connect(f.input);
    node = f.output;
  }
  node.connect(tail);
};

const buildChain = (ctx: BaseAudioContext, effects: readonly Effect[], beat: number): Fx[] =>
  effects.filter((e) => e.on).map((e) => buildEffect(ctx, e, beat)).filter((f): f is Fx => f !== null);

const updateChain = (fx: readonly Fx[], effects: readonly Effect[], beat: number) => {
  const live = effects.filter((e) => e.on);
  fx.forEach((f, i) => live[i] && f.update(live[i].params, beat));
};

export const createMaster = (ctx: BaseAudioContext, project: Project, sink: AudioNode): MasterNode => {
  const input = ctx.createGain();
  const gain = ctx.createGain();
  const meter = ctx.createAnalyser();
  meter.fftSize = 512;
  gain.connect(meter);
  meter.connect(sink);
  const node: MasterNode = { input, gain, meter, fx: [], fxKey: '\u0000' };
  syncMaster(ctx, node, project);
  return node;
};

export const syncMaster = (ctx: BaseAudioContext, node: MasterNode, project: Project) => {
  const beat = beatSeconds(project);
  const key = chainKey(project.master.effects);
  if (key !== node.fxKey) {
    node.fx.forEach((f) => f.dispose());
    node.fx = buildChain(ctx, project.master.effects, beat);
    node.fxKey = key;
    rewire(node.input, node.gain, node.fx);
  }
  updateChain(node.fx, project.master.effects, beat);
  node.gain.gain.value = project.master.volume;
};

export const createTrack = (ctx: BaseAudioContext, track: Track, project: Project, master: MasterNode, anySolo: boolean): TrackNode => {
  const input = ctx.createGain();
  const gain = ctx.createGain();
  const pan = ctx.createStereoPanner();
  const meter = ctx.createAnalyser();
  meter.fftSize = 256;
  gain.connect(pan).connect(meter).connect(master.input);
  const node: TrackNode = { input, gain, pan, meter, fx: [], fxKey: '\u0000' };
  syncTrack(ctx, node, track, project, anySolo);
  return node;
};

export const syncTrack = (ctx: BaseAudioContext, node: TrackNode, track: Track, project: Project, anySolo: boolean) => {
  const beat = beatSeconds(project);
  const key = chainKey(track.effects);
  if (key !== node.fxKey) {
    node.fx.forEach((f) => f.dispose());
    node.fx = buildChain(ctx, track.effects, beat);
    node.fxKey = key;
    rewire(node.input, node.gain, node.fx);
  }
  updateChain(node.fx, track.effects, beat);
  const audible = !track.mute && (!anySolo || track.solo);
  node.gain.gain.setTargetAtTime(audible ? track.volume : 0, ctx.currentTime, 0.015);
  node.pan.pan.setTargetAtTime(Math.max(-1, Math.min(1, track.pan)), ctx.currentTime, 0.015);
};

export const disposeTrack = (node: TrackNode) => {
  node.fx.forEach((f) => f.dispose());
  [node.input, node.gain, node.pan, node.meter].forEach((n) => n.disconnect());
};

export const level = (analyser: AnalyserNode, scratch: Float32Array<ArrayBuffer>): number => {
  analyser.getFloatTimeDomainData(scratch);
  let peak = 0;
  for (let i = 0; i < scratch.length; i += 1) peak = Math.max(peak, Math.abs(scratch[i]));
  return Math.min(1, peak);
};
