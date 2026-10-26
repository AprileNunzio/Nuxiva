import { createMaster, createTrack, type TrackNode } from './graph';
import { makeLibrary, scheduleRange, totalBeats } from './schedule';
import { encodeWav } from './wav';
import type { Catalog, Project } from '../types';

const RATE = 44100;
const TAIL = 3;

export const renderMix = async (project: Project, catalog: Catalog, buffers: ReadonlyMap<string, AudioBuffer>): Promise<Blob> => {
  const seconds = (totalBeats(project) * 60) / project.tempo + TAIL;
  const ctx = new OfflineAudioContext(2, Math.ceil(seconds * RATE), RATE);
  const master = createMaster(ctx, project, ctx.destination);
  const anySolo = project.tracks.some((t) => t.solo);
  const nodes = new Map<string, TrackNode>(project.tracks.map((t) => [t.id, createTrack(ctx, t, project, master, anySolo)]));
  const beat = 60 / project.tempo;
  scheduleRange({ project, library: makeLibrary(catalog), nodes, buffers, ctx, at: (b) => b * beat }, 0, totalBeats(project));
  return encodeWav(await ctx.startRendering());
};
