import React, { useEffect, useMemo, useRef } from 'react';
import { Headphones, VolumeX } from 'lucide-react';
import { cx, Meter } from './ui';
import type { Playhead } from '../usePlayhead';
import type { Catalog, Project, Track } from '../types';
import type { Mutator } from '../useStudio';

interface Props {
  readonly project: Project;
  readonly catalog: Catalog;
  readonly head: Playhead;
  readonly selected: string;
  readonly clip: string;
  readonly onSelect: (track: string, clip: string) => void;
  readonly onSeek: (beat: number) => void;
  readonly edit: (m: Mutator) => void;
}

const HEAD = 176;
const ROW = 52;

const ClipCanvas: React.FC<{ readonly track: Track; readonly clipId: string; readonly width: number; readonly color: string; readonly project: Project }> = ({ track, clipId, width, color, project }) => {
  const ref = useRef<HTMLCanvasElement>(null);
  const clip = track.clips.find((c) => c.id === clipId);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas || !clip) return;
    const ratio = window.devicePixelRatio || 1;
    const w = Math.max(2, Math.round(width));
    canvas.width = w * ratio;
    canvas.height = (ROW - 14) * ratio;
    const g = canvas.getContext('2d');
    if (!g) return;
    g.scale(ratio, ratio);
    g.clearRect(0, 0, w, ROW);
    g.fillStyle = color;
    if (clip.vocal) {
      const bars = Math.max(6, Math.floor(w / 3));
      for (let i = 0; i < bars; i += 1) {
        const h = 5 + Math.abs(Math.sin(i * 1.7 + clip.start)) * (ROW - 28);
        g.globalAlpha = 0.75;
        g.fillRect(i * 3, (ROW - 14 - h) / 2, 2, h);
      }
      return;
    }
    const pitches = clip.notes.map((n) => n.p);
    const low = Math.min(...pitches, 127);
    const span = Math.max(1, Math.max(...pitches, 0) - low);
    const scale = w / Math.max(0.01, clip.length);
    g.globalAlpha = 0.85;
    for (const n of clip.notes) {
      const y = (ROW - 18) - ((n.p - low) / span) * (ROW - 22);
      g.fillRect(n.t * scale, y, Math.max(1.5, n.d * scale), 3);
    }
  }, [clip, width, color, project.tempo]);
  return <canvas ref={ref} className="pointer-events-none absolute inset-x-0 bottom-1 h-[38px] w-full" aria-hidden />;
};

export const Arrangement: React.FC<Props> = ({ project, catalog, head, selected, clip, onSelect, onSeek, edit }) => {
  const total = project.bars * project.beats;
  const scroller = useRef<HTMLDivElement>(null);
  const pxPerBeat = 14;
  const width = Math.max(600, total * pxPerBeat);
  const instruments = useMemo(() => new Map(catalog.instruments.map((i) => [i.id, i])), [catalog]);
  const toggle = (id: string, key: 'mute' | 'solo') =>
    edit((p) => ({ ...p, tracks: p.tracks.map((t) => (t.id === id ? { ...t, [key]: !t[key] } : t)) }));

  useEffect(() => {
    const el = scroller.current;
    if (!el || !head.playing) return;
    const x = head.beat * pxPerBeat;
    if (x < el.scrollLeft || x > el.scrollLeft + el.clientWidth - 40) el.scrollLeft = Math.max(0, x - 80);
  }, [head.beat, head.playing]);

  return (
    <div ref={scroller} className="relative flex-1 overflow-auto bg-white">
      <div style={{ width: HEAD + width }} className="relative">
        <div className="sticky top-0 z-20 flex h-7 border-b border-slate-200 bg-slate-50">
          <div style={{ width: HEAD }} className="sticky left-0 z-30 shrink-0 border-r border-slate-200 bg-slate-50" />
          <div
            className="relative flex-1 cursor-pointer"
            onPointerDown={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              onSeek(((e.clientX - rect.left) / width) * total);
            }}
          >
            {project.structure.map((s) => (
              <div
                key={`${s.name}-${s.start}`}
                className="absolute top-0 h-full truncate border-l border-violet-200 bg-violet-50/70 px-1.5 text-[10px] font-semibold uppercase leading-7 text-violet-700"
                style={{ left: s.start * project.beats * pxPerBeat, width: s.bars * project.beats * pxPerBeat }}
              >
                {s.name}
              </div>
            ))}
          </div>
        </div>
        {project.tracks.map((track) => {
          const instrument = instruments.get(track.instrument);
          return (
            <div key={track.id} className={cx('flex border-b border-slate-100', selected === track.id && 'bg-violet-50/40')} style={{ height: ROW }}>
              <button
                type="button"
                onClick={() => onSelect(track.id, track.clips[0]?.id ?? '')}
                style={{ width: HEAD }}
                className="sticky left-0 z-10 flex shrink-0 flex-col justify-center gap-1 border-r border-slate-200 bg-white px-2 text-left"
              >
                <div className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: track.color }} />
                  <span className="truncate text-xs font-semibold text-slate-800">{track.name}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="flex-1 truncate text-[10px] text-slate-500">{instrument?.name ?? track.instrument}</span>
                  <span
                    role="button"
                    tabIndex={0}
                    aria-label="mute"
                    onClick={(e) => { e.stopPropagation(); toggle(track.id, 'mute'); }}
                    onKeyDown={(e) => e.key === 'Enter' && toggle(track.id, 'mute')}
                    className={cx('rounded p-0.5', track.mute ? 'bg-rose-100 text-rose-600' : 'text-slate-400 hover:text-slate-600')}
                  >
                    <VolumeX size={12} />
                  </span>
                  <span
                    role="button"
                    tabIndex={0}
                    aria-label="solo"
                    onClick={(e) => { e.stopPropagation(); toggle(track.id, 'solo'); }}
                    onKeyDown={(e) => e.key === 'Enter' && toggle(track.id, 'solo')}
                    className={cx('rounded p-0.5', track.solo ? 'bg-amber-100 text-amber-600' : 'text-slate-400 hover:text-slate-600')}
                  >
                    <Headphones size={12} />
                  </span>
                </div>
                <Meter value={head.tracks.get(track.id) ?? 0} />
              </button>
              <div className="relative flex-1" style={{ width }}>
                {track.clips.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => onSelect(track.id, c.id)}
                    className={cx(
                      'absolute top-1 bottom-1 overflow-hidden rounded-md border text-left transition',
                      clip === c.id ? 'border-violet-500 ring-2 ring-violet-300' : 'border-black/10 hover:border-violet-300',
                    )}
                    style={{ left: c.start * pxPerBeat, width: Math.max(4, c.length * pxPerBeat), background: `${track.color}22` }}
                  >
                    <span className="absolute left-1 top-0.5 z-10 truncate text-[9px] font-medium text-slate-600">{c.name}</span>
                    <ClipCanvas track={track} clipId={c.id} width={c.length * pxPerBeat} color={track.color} project={project} />
                  </button>
                ))}
              </div>
            </div>
          );
        })}
        <div className="pointer-events-none absolute bottom-0 top-0 z-10 w-px bg-rose-500" style={{ left: HEAD + head.beat * pxPerBeat }} />
      </div>
    </div>
  );
};
