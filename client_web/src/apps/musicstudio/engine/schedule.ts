import { playDrum, playRiser, playSynth } from './voices';
import type { TrackNode } from './graph';
import type { Catalog, Clip, Instrument, Note, Project, Track } from '../types';

export interface Library {
  readonly instruments: ReadonlyMap<string, Instrument>;
  readonly lanes: ReadonlyMap<number, string>;
}

export const makeLibrary = (catalog: Catalog): Library => ({
  instruments: new Map(catalog.instruments.map((i) => [i.id, i])),
  lanes: new Map(Object.entries(catalog.lanes).map(([lane, midi]) => [midi, lane])),
});

export const totalBeats = (project: Project) => project.bars * project.beats;

const swung = (note: Note, clip: Clip, project: Project) => {
  const eighth = Math.round((clip.start + note.t) * 2);
  const exact = Math.abs((clip.start + note.t) * 2 - eighth) < 0.02;
  return exact && eighth % 2 === 1 ? project.swing * 0.34 * 0.5 : 0;
};

export interface Scheduler {
  readonly project: Project;
  readonly library: Library;
  readonly nodes: ReadonlyMap<string, TrackNode>;
  readonly buffers: ReadonlyMap<string, AudioBuffer>;
  readonly ctx: BaseAudioContext;
  readonly at: (beat: number) => number;
}

const playClipNote = (s: Scheduler, track: Track, clip: Clip, note: Note, node: TrackNode) => {
  const instrument = s.library.instruments.get(track.instrument);
  if (!instrument) return;
  const beat = 60 / s.project.tempo;
  const when = s.at(clip.start + note.t + swung(note, clip, s.project));
  const dur = note.d * beat;
  const voice = instrument.voice;
  if (voice.engine === 'drums') {
    const lane = s.library.lanes.get(note.p);
    if (lane) playDrum(s.ctx, node.input, voice, lane, when, note.v);
  } else if (voice.engine === 'noise') {
    playRiser(s.ctx, node.input, when, dur, note.v);
  } else if (voice.engine === 'synth') {
    playSynth(s.ctx, node.input, voice, note.p, when, dur, note.v);
  }
};

const playClipAudio = (s: Scheduler, clip: Clip, node: TrackNode, offsetBeats: number) => {
  const asset = clip.vocal?.asset;
  const buffer = asset ? s.buffers.get(asset) : undefined;
  if (!buffer) return;
  const src = s.ctx.createBufferSource();
  src.buffer = buffer;
  src.connect(node.input);
  const beat = 60 / s.project.tempo;
  const offset = Math.max(0, offsetBeats * beat);
  if (offset >= buffer.duration) return;
  src.start(s.at(clip.start + offsetBeats), offset);
};

export const scheduleRange = (s: Scheduler, from: number, to: number): void => {
  for (const track of s.project.tracks) {
    const node = s.nodes.get(track.id);
    if (!node) continue;
    for (const clip of track.clips) {
      if (clip.start + clip.length <= from || clip.start >= to + 1) continue;
      if (clip.vocal) {
        if (clip.start >= from && clip.start < to) playClipAudio(s, clip, node, 0);
        else if (clip.start < from && from === 0) playClipAudio(s, clip, node, from - clip.start);
        continue;
      }
      for (const note of clip.notes) {
        const abs = clip.start + note.t;
        if (abs >= from && abs < to) playClipNote(s, track, clip, note, node);
      }
    }
  }
};

export const resumeAudio = (s: Scheduler, position: number): void => {
  for (const track of s.project.tracks) {
    const node = s.nodes.get(track.id);
    if (!node) continue;
    for (const clip of track.clips) {
      if (clip.vocal && clip.start < position && position < clip.start + clip.length) playClipAudio(s, clip, node, position - clip.start);
    }
  }
};
