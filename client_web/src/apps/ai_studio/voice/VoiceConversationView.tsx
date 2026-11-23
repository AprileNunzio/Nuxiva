import React, { useEffect, useMemo, useState } from 'react';
import { useStudioI18n } from '../scope';
import { VoiceTurnCard } from './VoiceTurnCard';
import { useVoiceTurns } from './useVoiceTurns';
import type { VoiceChannelFilter, VoiceTurn } from './types';

type Filter = 'voice' | 'all' | 'review';

interface VoiceConversationViewProps {
  onContinueInChat: (turn: VoiceTurn) => void;
}

function dayKey(at: number): string {
  const d = new Date(at * 1000);
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

function exportLog(turns: VoiceTurn[]) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(turns, null, 2)], { type: 'application/json;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = `nuxiva_voice_${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export const VoiceConversationView: React.FC<VoiceConversationViewProps> = ({ onContinueInChat }) => {
  const { t } = useStudioI18n();
  const [filter, setFilter] = useState<Filter>('voice');
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [live, setLive] = useState(true);
  const channel: VoiceChannelFilter = filter === 'all' ? '' : 'voice';
  const { turns, stats, error, loading, hasMore, refresh, loadMore, patch } = useVoiceTurns(channel, query, live);

  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(search), 350);
    return () => window.clearTimeout(timer);
  }, [search]);

  const visible = useMemo(
    () => (filter === 'review' ? turns.filter((turn) => turn.heard && !turn.heard.verdict) : turns),
    [filter, turns],
  );

  const dayLabel = (at: number) => {
    const today = new Date();
    const yesterday = new Date(Date.now() - 86400000);
    const key = dayKey(at);
    if (key === dayKey(today.getTime() / 1000)) return t('voice_today');
    if (key === dayKey(yesterday.getTime() / 1000)) return t('voice_yesterday');
    return new Date(at * 1000).toLocaleDateString([], { weekday: 'long', day: 'numeric', month: 'long' });
  };

  const chip = (value: Filter, label: string) => (
    <button
      key={value}
      type="button"
      onClick={() => setFilter(value)}
      aria-pressed={filter === value}
      className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors ${filter === value ? 'border-cyan-500/70 bg-cyan-500/15 text-cyan-200' : 'border-slate-700 text-slate-400 hover:text-slate-200'}`}
    >
      {label}
    </button>
  );

  return (
    <div className="flex-1 h-full flex flex-col min-w-0 bg-slate-950/40">
      <div className="px-4 py-3 border-b border-slate-800/80 bg-slate-900/70 backdrop-blur-md flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xl" aria-hidden>🎙️</span>
          <div className="min-w-0 flex-1 basis-[calc(100%-2.5rem)] sm:basis-0">
            <h1 className="text-sm font-semibold text-slate-100 flex flex-wrap items-center gap-x-2">
              {t('voice_title')}
              <span className="whitespace-nowrap px-1.5 py-0.5 rounded-full bg-cyan-500/15 border border-cyan-500/40 text-[9px] font-mono text-cyan-300">{t('voice_badge')}</span>
            </h1>
            <p className="text-[11px] text-slate-400 truncate">{t('voice_subtitle')}</p>
          </div>
          <button
            type="button"
            onClick={() => setLive((v) => !v)}
            aria-pressed={live}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] ${live ? 'border-emerald-500/50 text-emerald-300' : 'border-slate-700 text-slate-400'}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${live ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
            {live ? t('voice_live_on') : t('voice_live_off')}
          </button>
          <button type="button" onClick={() => void refresh()} className="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-[11px] text-slate-300 hover:text-white">
            ⟳ {t('voice_refresh')}
          </button>
          <button type="button" disabled={!turns.length} onClick={() => exportLog(turns)} className="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-[11px] text-slate-300 hover:text-white disabled:opacity-40">
            📥 {t('voice_export')}
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {chip('voice', t('voice_filter_voice'))}
          {chip('all', t('voice_filter_all'))}
          {chip('review', t('voice_filter_review'))}
          <input
            type="search"
            value={search}
            maxLength={120}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('voice_search')}
            className="flex-1 min-w-[10rem] bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-600"
          />
        </div>
        {typeof stats.total === 'number' && (
          <p className="text-[10px] font-mono text-slate-500">
            {t('voice_stats', { total: stats.total ?? 0, pending: stats.pending ?? 0, audio_mb: stats.audio_mb ?? 0 })}
            {' · '}
            {t('voice_count', { count: visible.length })}
          </p>
        )}
      </div>

      {error && (
        <div role="alert" className="mx-4 mt-3 px-3 py-2 rounded-xl border border-rose-700/60 bg-rose-950/50 text-xs text-rose-200 flex items-center justify-between gap-2">
          <span>{t('voice_error')}: {error}</span>
          <button type="button" onClick={() => void refresh()} className="underline">{t('err_retry')}</button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3 md:p-4 flex flex-col gap-3">
        {!loading && visible.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8 gap-2 text-slate-500">
            <span className="text-4xl" aria-hidden>🎙️</span>
            <p className="text-sm max-w-md">{t('voice_empty')}</p>
          </div>
        ) : (
          visible.map((turn, index) => (
            <React.Fragment key={turn.id}>
              {(index === 0 || dayKey(visible[index - 1].at) !== dayKey(turn.at)) && (
                <div className="sticky top-0 z-10 self-center px-3 py-0.5 rounded-full bg-slate-900/90 border border-slate-800 text-[10px] uppercase tracking-wider text-slate-400">
                  {dayLabel(turn.at)}
                </div>
              )}
              <VoiceTurnCard
                turn={turn}
                onHeardChange={(heard) => patch(turn.id, (current) => ({ ...current, heard }))}
                onDeleted={() => patch(turn.id, () => null)}
                onContinue={onContinueInChat}
              />
            </React.Fragment>
          ))
        )}
        {hasMore && filter !== 'review' && (
          <button type="button" onClick={() => void loadMore()} className="self-center px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-300 hover:text-white">
            {t('voice_load_more')}
          </button>
        )}
      </div>
    </div>
  );
};
