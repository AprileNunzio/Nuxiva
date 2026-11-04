import { createMaster, createTrack, disposeTrack, level, syncMaster, syncTrack, type MasterNode, type TrackNode } from './graph';
import { makeLibrary, resumeAudio, scheduleRange, totalBeats, type Library } from './schedule';
import type { Catalog, Project } from '../types';
import { playSynth, playDrum } from './voices';

const LOOKAHEAD = 0.25;
const TICK_MS = 30;

export class Player {
  private ctx: AudioContext | null = null;
  private master: MasterNode | null = null;
  private nodes = new Map<string, TrackNode>();
  private buffers = new Map<string, AudioBuffer>();
  private library: Library;
  private project: Project;
  private timer = 0;
  private anchor = 0;
  private cursor = 0;
  private position = 0;
  private playing = false;
  private loop = false;
  private scratch = new Float32Array(256) as Float32Array<ArrayBuffer>;

  constructor(catalog: Catalog, project: Project) {
    this.library = makeLibrary(catalog);
    this.project = project;
  }

  get isPlaying() {
    return this.playing;
  }

  get audioBuffers(): ReadonlyMap<string, AudioBuffer> {
    return this.buffers;
  }

  setLoop(on: boolean) {
    this.loop = on;
  }

  private context(): AudioContext {
    if (!this.ctx) {
      this.ctx = new AudioContext({ latencyHint: 'interactive' });
      this.master = createMaster(this.ctx, this.project, this.ctx.destination);
    }
    return this.ctx;
  }

  async decode(name: string, bytes: ArrayBuffer) {
    if (this.buffers.has(name)) return;
    this.buffers.set(name, await this.context().decodeAudioData(bytes.slice(0)));
  }

  hasBuffer(name: string) {
    return this.buffers.has(name);
  }

  setProject(project: Project) {
    const tempoChanged = project.tempo !== this.project.tempo;
    const here = this.currentBeat();
    this.project = project;
    if (!this.ctx || !this.master) return;
    syncMaster(this.ctx, this.master, project);
    const solo = project.tracks.some((t) => t.solo);
    const ids = new Set(project.tracks.map((t) => t.id));
    for (const [id, node] of this.nodes) {
      if (!ids.has(id)) {
        disposeTrack(node);
        this.nodes.delete(id);
      }
    }
    for (const track of project.tracks) {
      const node = this.nodes.get(track.id);
      if (node) syncTrack(this.ctx, node, track, project, solo);
      else this.nodes.set(track.id, createTrack(this.ctx, track, project, this.master, solo));
    }
    if (tempoChanged && this.playing) this.anchorAt(here);
  }

  private anchorAt(beat: number) {
    if (!this.ctx) return;
    this.anchor = this.ctx.currentTime - (beat * 60) / this.project.tempo;
    this.cursor = beat;
  }

  private at = (beat: number) => this.anchor + (beat * 60) / this.project.tempo;

  currentBeat(): number {
    if (!this.ctx || !this.playing) return this.position;
    return ((this.ctx.currentTime - this.anchor) * this.project.tempo) / 60;
  }

  private scheduler() {
    return { project: this.project, library: this.library, nodes: this.nodes, buffers: this.buffers, ctx: this.ctx as AudioContext, at: this.at };
  }

  private tick = () => {
    if (!this.ctx || !this.playing) return;
    const total = totalBeats(this.project);
    const horizon = ((this.ctx.currentTime + LOOKAHEAD - this.anchor) * this.project.tempo) / 60;
    const to = Math.min(horizon, total);
    if (to > this.cursor) {
      scheduleRange(this.scheduler(), this.cursor, to);
      this.cursor = to;
    }
    if (this.currentBeat() >= total + 1) {
      if (this.loop) {
        this.anchor = this.ctx.currentTime;
        this.cursor = 0;
        scheduleRange(this.scheduler(), 0, 0);
      } else this.stop();
    }
  };

  async play(from?: number) {
    const ctx = this.context();
    await ctx.resume();
    this.setProject(this.project);
    if (this.playing) this.pause();
    const start = from ?? (this.position >= totalBeats(this.project) ? 0 : this.position);
    this.playing = true;
    this.anchorAt(start);
    this.cursor = start;
    resumeAudio(this.scheduler(), start);
    window.clearInterval(this.timer);
    this.timer = window.setInterval(this.tick, TICK_MS);
    this.tick();
  }

  pause() {
    this.position = this.currentBeat();
    this.playing = false;
    window.clearInterval(this.timer);
    this.cut();
  }

  stop() {
    this.playing = false;
    window.clearInterval(this.timer);
    this.position = 0;
    this.cut();
  }

  seek(beat: number) {
    const target = Math.max(0, Math.min(beat, totalBeats(this.project)));
    if (this.playing) void this.play(target);
    else this.position = target;
  }

  private cut() {
    if (!this.ctx || !this.master) return;
    for (const node of this.nodes.values()) disposeTrack(node);
    this.nodes.clear();
    this.master.fx.forEach((f) => f.dispose());
    this.master.input.disconnect();
    this.master.gain.disconnect();
    this.master.meter.disconnect();
    this.master = createMaster(this.ctx, this.project, this.ctx.destination);
    const solo = this.project.tracks.some((t) => t.solo);
    for (const track of this.project.tracks) this.nodes.set(track.id, createTrack(this.ctx, track, this.project, this.master, solo));
  }

  levels(): { master: number; tracks: Map<string, number> } {
    const tracks = new Map<string, number>();
    if (!this.master) return { master: 0, tracks };
    for (const [id, node] of this.nodes) tracks.set(id, level(node.meter, this.scratch));
    const scratch = new Float32Array(this.master.meter.fftSize) as Float32Array<ArrayBuffer>;
    return { master: level(this.master.meter, scratch), tracks };
  }

  async preview(trackId: string, midi: number) {
    const ctx = this.context();
    await ctx.resume();
    const node = this.nodes.get(trackId) ?? (this.master ? createTrack(ctx, this.project.tracks.find((t) => t.id === trackId)!, this.project, this.master, false) : null);
    const track = this.project.tracks.find((t) => t.id === trackId);
    const instrument = track && this.library.instruments.get(track.instrument);
    if (!node || !instrument) return;
    if (instrument.voice.engine === 'drums') {
      const lane = this.library.lanes.get(midi);
      if (lane) playDrum(ctx, node.input, instrument.voice, lane, ctx.currentTime, 0.9);
    } else playSynth(ctx, node.input, instrument.voice, midi, ctx.currentTime, 0.4, 0.8);
  }

  dispose() {
    window.clearInterval(this.timer);
    this.playing = false;
    void this.ctx?.close();
    this.ctx = null;
  }
}
