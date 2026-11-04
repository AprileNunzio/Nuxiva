import React from 'react';
import { Headphones, VolumeX } from 'lucide-react';
import { cx, Meter, Slider } from './ui';
import type { Playhead } from '../usePlayhead';
import type { Project, Track } from '../types';
import type { Mutator } from '../useStudio';

interface Props {
  readonly project: Project;
  readonly head: Playhead;
  readonly selected: string;
  readonly onSelect: (id: string) => void;
  readonly edit: (m: Mutator) => void;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

export const Mixer: React.FC<Props> = ({ project, head, selected, onSelect, edit, t }) => {
  const patch = (id: string, change: Partial<Track>) =>
    edit((p) => ({ ...p, tracks: p.tracks.map((tr) => (tr.id === id ? { ...tr, ...change } : tr)) }));
  return (
    <div className="flex flex-1 gap-2 overflow-x-auto bg-slate-50 p-3">
      {project.tracks.map((track) => (
        <div
          key={track.id}
          onClick={() => onSelect(track.id)}
          className={cx('flex w-24 shrink-0 cursor-pointer flex-col items-center gap-2 rounded-2xl border bg-white p-2 shadow-sm', selected === track.id ? 'border-violet-400' : 'border-slate-200')}
        >
          <div className="h-1 w-full rounded-full" style={{ background: track.color }} />
          <div className="w-full truncate text-center text-[11px] font-semibold text-slate-700">{track.name}</div>
          <Slider label={t('pan')} min={-1} max={1} step={0.01} value={track.pan} onChange={(pan) => patch(track.id, { pan })} />
          <div className="flex h-28 items-stretch gap-2">
            <Meter vertical value={head.tracks.get(track.id) ?? 0} />
            <input
              type="range"
              aria-label={t('volume')}
              min={0}
              max={1.5}
              step={0.01}
              value={track.volume}
              onChange={(e) => patch(track.id, { volume: Number(e.target.value) })}
              className="accent-violet-600"
              style={{ writingMode: 'vertical-lr', direction: 'rtl', width: 20 }}
            />
          </div>
          <div className="flex gap-1">
            <button
              type="button"
              aria-label="mute"
              onClick={(e) => { e.stopPropagation(); patch(track.id, { mute: !track.mute }); }}
              className={cx('rounded-md p-1.5', track.mute ? 'bg-rose-100 text-rose-600' : 'bg-slate-100 text-slate-500')}
            >
              <VolumeX size={13} />
            </button>
            <button
              type="button"
              aria-label="solo"
              onClick={(e) => { e.stopPropagation(); patch(track.id, { solo: !track.solo }); }}
              className={cx('rounded-md p-1.5', track.solo ? 'bg-amber-100 text-amber-600' : 'bg-slate-100 text-slate-500')}
            >
              <Headphones size={13} />
            </button>
          </div>
        </div>
      ))}
      <div className="flex w-24 shrink-0 flex-col items-center gap-2 rounded-2xl border border-fuchsia-200 bg-white p-2 shadow-sm">
        <div className="h-1 w-full rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500" />
        <div className="text-[11px] font-semibold text-slate-700">{t('master')}</div>
        <div className="h-4" />
        <div className="flex h-28 items-stretch gap-2">
          <Meter vertical value={head.master} />
          <input
            type="range"
            aria-label={t('master')}
            min={0}
            max={1.5}
            step={0.01}
            value={project.master.volume}
            onChange={(e) => edit((p) => ({ ...p, master: { ...p.master, volume: Number(e.target.value) } }))}
            className="accent-fuchsia-600"
            style={{ writingMode: 'vertical-lr', direction: 'rtl', width: 20 }}
          />
        </div>
      </div>
    </div>
  );
};
