import React from 'react';
import { Pill } from '../../shared/kit';
import { EarLive } from '../types';

interface Props {
  readonly live: EarLive;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

export const liveState = (live: EarLive): { readonly key: string; readonly tone: 'emerald' | 'amber' | 'slate' | 'rose' } => {
  if (!live.available) return { key: 'live_unavailable', tone: 'rose' };
  if (live.mode === 'off') return { key: 'live_off', tone: 'slate' };
  if (live.active) return { key: 'live_on', tone: 'emerald' };
  return { key: live.reason === 'slow' ? 'live_paused_slow' : 'live_paused_load', tone: 'amber' };
};

export const LivePanel: React.FC<Props> = ({ live, t }) => {
  const state = liveState(live);
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm text-slate-300">
      <Pill tone={state.tone}>{t(state.key)}</Pill>
      <span className="text-xs text-slate-500">{t(`live_mode_${live.mode}`)}</span>
      {live.available && live.mode !== 'off' ? (
        <span className="text-xs text-slate-500">
          {t('live_detail', { ms: live.decodeMs, s: live.interval.toFixed(1), load: live.load.toFixed(2) })}
        </span>
      ) : null}
    </div>
  );
};
