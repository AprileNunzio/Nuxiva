import React from 'react';
import { Pause, Play, Repeat, Square, Upload, Cast } from 'lucide-react';
import { Btn, Meter, cx } from './ui';
import type { Playhead } from '../usePlayhead';
import type { Project } from '../types';
import type { Studio } from '../useStudio';

interface Props {
  readonly studio: Studio;
  readonly project: Project;
  readonly head: Playhead;
  readonly loop: boolean;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly onLoop: () => void;
  readonly onCast: () => void;
}

const clock = (beat: number, project: Project) => {
  const seconds = (Math.max(0, beat) * 60) / project.tempo;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  const bar = Math.floor(beat / project.beats) + 1;
  const inBar = Math.floor(beat % project.beats) + 1;
  return { time: `${m}:${String(s).padStart(2, '0')}`, pos: `${bar}.${inBar}` };
};

export const Transport: React.FC<Props> = ({ studio, project, head, loop, t, onLoop, onCast }) => {
  const player = studio.player.current;
  const { time, pos } = clock(head.beat, project);
  const ready = project.job.state !== 'building' && project.tracks.length > 0;
  const keyName = studio.catalog ? `${studio.catalog.notes[project.key.root] ?? ''} ${project.key.mode.replace(/_/g, ' ')}` : '';
  return (
    <header className="flex flex-wrap items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-2.5 backdrop-blur">
      <div className="flex items-center gap-1.5">
        <Btn tone="accent" disabled={!ready} aria-label={head.playing ? t('pause') : t('play')} onClick={() => (head.playing ? player?.pause() : void player?.play())}>
          {head.playing ? <Pause size={15} /> : <Play size={15} />}
        </Btn>
        <Btn disabled={!ready} aria-label={t('stop')} onClick={() => player?.stop()}>
          <Square size={14} />
        </Btn>
        <Btn active={loop} aria-label={t('loop')} onClick={onLoop}>
          <Repeat size={14} />
        </Btn>
      </div>
      <div className="rounded-xl bg-slate-900 px-3 py-1 font-mono text-sm tabular-nums text-emerald-300" aria-live="off">
        {time} <span className="text-slate-500">·</span> {pos}
      </div>
      <div className="flex items-center gap-2 text-xs text-slate-600">
        <span className="rounded-md bg-violet-50 px-2 py-1 font-semibold text-violet-700">{Math.round(project.tempo)} BPM</span>
        <span className="rounded-md bg-slate-100 px-2 py-1 capitalize">{keyName}</span>
        <span className="rounded-md bg-slate-100 px-2 py-1 capitalize">{project.genre.replace(/_/g, ' ')}</span>
      </div>
      <div className="mx-2 hidden w-28 md:block" aria-hidden>
        <Meter value={head.master} />
      </div>
      <div className="ml-auto flex items-center gap-1.5">
        {project.job.state === 'building' && (
          <span className="flex items-center gap-2 text-xs text-violet-700">
            <span className="h-2 w-2 animate-pulse rounded-full bg-fuchsia-500" />
            {project.job.stage ? t(`stage_${project.job.stage}`) : t('building')}
          </span>
        )}
        <Btn disabled={!ready || studio.busy} onClick={() => void studio.publish()}>
          <Upload size={14} />
          {t('publish')}
        </Btn>
        <Btn disabled={!ready} onClick={onCast} className={cx(studio.published && 'border-emerald-300')}>
          <Cast size={14} />
          {t('cast')}
        </Btn>
      </div>
    </header>
  );
};
