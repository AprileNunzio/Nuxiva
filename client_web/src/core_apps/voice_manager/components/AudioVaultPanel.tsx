import React, { useState } from 'react';
import { Database, HardDrive, Play, RefreshCw, Search, Shield, Trash2, Zap } from 'lucide-react';
import { Btn, Empty, Field, inputClass, Pill } from '../../shared/kit';
import { AudioVaultClip, AudioVaultStats } from '../types';

interface Props {
  readonly stats: AudioVaultStats | null;
  readonly clips: AudioVaultClip[];
  readonly busy: boolean;
  readonly onPlayClip: (clipId: string) => void;
  readonly onDeleteClip: (clipId: string) => Promise<void>;
  readonly onPregenerate: () => Promise<void>;
  readonly onClear: () => Promise<void>;
  readonly onSearch: (query: string) => void;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

export const AudioVaultPanel: React.FC<Props> = ({
  stats,
  clips,
  busy,
  onPlayClip,
  onDeleteClip,
  onPregenerate,
  onClear,
  onSearch,
  t,
}) => {
  const [query, setQuery] = useState('');
  const [pregenerating, setPregenerating] = useState(false);

  const handlePregenerate = async () => {
    setPregenerating(true);
    try {
      await onPregenerate();
    } finally {
      setPregenerating(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* STATISTICHE RISPARMIO CREDITI & TOKEN */}
      <div className="grid grid-cols-1 cq-sm:grid-cols-2 cq-lg:grid-cols-4 gap-3">
        <div className="p-3 rounded-xl border border-emerald-500/30 bg-emerald-950/20">
          <div className="flex items-center justify-between text-xs text-emerald-400 mb-1">
            <span>{t('vault_chars_saved')}</span>
            <Zap className="h-4 w-4" />
          </div>
          <div className="text-xl font-bold font-mono text-emerald-300">
            {stats?.total_chars_saved.toLocaleString() ?? 0}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            ~{Math.round((stats?.total_chars_saved ?? 0) / 4)} {t('tokens_saved')}
          </div>
        </div>

        <div className="p-3 rounded-xl border border-cyan-500/30 bg-cyan-950/20">
          <div className="flex items-center justify-between text-xs text-cyan-400 mb-1">
            <span>{t('vault_total_hits')}</span>
            <RefreshCw className="h-4 w-4" />
          </div>
          <div className="text-xl font-bold font-mono text-cyan-300">
            {stats?.total_hits.toLocaleString() ?? 0}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            {t('zero_cost_replays')}
          </div>
        </div>

        <div className="p-3 rounded-xl border border-purple-500/30 bg-purple-950/20">
          <div className="flex items-center justify-between text-xs text-purple-400 mb-1">
            <span>{t('vault_free_plans')}</span>
            <Shield className="h-4 w-4" />
          </div>
          <div className="text-xl font-bold font-mono text-purple-300">
            {stats?.equivalent_free_plans_saved ?? 0}x
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            {t('monthly_plans_preserved')}
          </div>
        </div>

        <div className="p-3 rounded-xl border border-slate-700 bg-slate-900/40">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>{t('vault_clips_stored')}</span>
            <HardDrive className="h-4 w-4" />
          </div>
          <div className="text-xl font-bold font-mono text-slate-200">
            {stats?.total_clips ?? 0}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            {stats?.total_size_mb ?? 0} MB {t('on_disk')}
          </div>
        </div>
      </div>

      {/* AZIONI RAPIDE CASSAFORTE */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-xl border border-slate-800 bg-slate-900/60">
        <div className="flex items-center gap-2">
          <Btn tone="cyan" busy={pregenerating} onClick={handlePregenerate}>
            <Zap className="h-3.5 w-3.5 mr-1" />
            {t('pregenerate_common_btn')}
          </Btn>
          <span className="text-xs text-slate-400 hidden sm:inline">
            {t('pregenerate_hint')}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Btn tone="slate" onClick={onClear} title={t('clear_vault_hint')}>
            <Trash2 className="h-3.5 w-3.5 mr-1" />
            {t('clear_unpinned')}
          </Btn>
        </div>
      </div>

      {/* SEARCH BAR & LISTA CLIP */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                onSearch(e.target.value);
              }}
              placeholder={t('search_clips_placeholder')}
              className={`${inputClass} pl-8 text-xs`}
            />
          </div>
        </div>

        {clips.length === 0 ? (
          <Empty>{t('no_clips_in_vault')}</Empty>
        ) : (
          <div className="space-y-1.5 max-h-[380px] overflow-y-auto pr-1">
            {clips.map((clip) => (
              <div
                key={clip.id}
                className="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-slate-800 bg-slate-900/40 hover:bg-slate-900/70 transition"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-medium text-xs text-slate-200 truncate">
                      "{clip.text}"
                    </p>
                    {clip.pinned && (
                      <span className="text-[10px] px-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        {t('pinned')}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-slate-400">
                    <Pill tone={clip.engine === 'elevenlabs' ? 'purple' : 'emerald'}>
                      {clip.engine}
                    </Pill>
                    <span className="font-mono text-cyan-300">
                      {clip.hit_count} {t('replays')}
                    </span>
                    <span>·</span>
                    <span className="font-mono text-emerald-400">
                      +{clip.chars_saved.toLocaleString()} {t('chars_saved')}
                    </span>
                    <span>·</span>
                    <span className="text-slate-500">
                      {clip.voice_id}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <Btn tone="slate" onClick={() => onPlayClip(clip.id)} title={t('preview')}>
                    <Play className="h-3 w-3" />
                  </Btn>
                  <Btn tone="rose" onClick={() => onDeleteClip(clip.id)} title={t('delete')}>
                    <Trash2 className="h-3 w-3" />
                  </Btn>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
