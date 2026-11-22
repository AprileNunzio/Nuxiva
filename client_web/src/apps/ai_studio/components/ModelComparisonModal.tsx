import React, { useState } from 'react';
import { useStudioI18n } from '../scope';
import * as api from '../api';
import type { ModelMode } from '../types';
import { Markdown } from './Markdown';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  projectId: string | null;
}

const ALL_MODES: ModelMode[] = ['fast', 'reasoning', 'creative', 'code'];

export const ModelComparisonModal: React.FC<Props> = ({ isOpen, onClose, projectId }) => {
  const { t } = useStudioI18n();
  const [prompt, setPrompt] = useState('');
  const [selectedModes, setSelectedModes] = useState<ModelMode[]>(['fast', 'reasoning']);
  const [results, setResults] = useState<api.ModelComparisonResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const toggleMode = (m: ModelMode) => {
    setSelectedModes((prev) =>
      prev.includes(m) ? (prev.length > 1 ? prev.filter((x) => x !== m) : prev) : [...prev, m]
    );
  };

  const handleCompare = async () => {
    if (!prompt.trim() || isLoading) return;
    setIsLoading(true);
    setError('');
    try {
      const res = await api.compareModels(prompt.trim(), selectedModes, projectId);
      setResults(res);
    } catch (err) {
      setError(String((err as Error).message || err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose} role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        className="w-[min(64rem,96vw)] max-h-[88vh] flex flex-col rounded-2xl border border-white/10 bg-slate-900/90 backdrop-blur-xl shadow-[0_0_60px_-15px_rgba(0,240,255,0.35)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/10">
          <div className="text-sm font-semibold text-slate-100">⚖️ {t('compare_title')}</div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-100" aria-label={t('close')}>
            ✕
          </button>
        </div>

        <div className="p-4 flex flex-col gap-3 overflow-y-auto">
          <p className="text-xs text-slate-400">{t('compare_desc')}</p>

          <div className="flex flex-col gap-2 rounded-xl border border-white/10 p-3 bg-slate-950/60">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={3}
              placeholder={t('compare_placeholder')}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
            />
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 text-xs">
                {ALL_MODES.map((m) => {
                  const active = selectedModes.includes(m);
                  return (
                    <button
                      key={m}
                      type="button"
                      onClick={() => toggleMode(m)}
                      className={`px-2 py-1 rounded-md text-xs font-medium border transition-colors ${
                        active
                          ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50'
                          : 'bg-slate-900 text-slate-400 border-slate-700 hover:text-slate-200'
                      }`}
                    >
                      {m}
                    </button>
                  );
                })}
              </div>
              <button
                type="button"
                disabled={!prompt.trim() || isLoading}
                onClick={handleCompare}
                className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-xs font-semibold text-white disabled:opacity-40 shadow-sm"
              >
                {isLoading ? t('compare_running') : t('compare_btn')}
              </button>
            </div>
          </div>

          {error && <p className="text-xs text-red-400">{error}</p>}

          {results.length > 0 && (
            <div className="os-tiles [--tile-min:18rem] [--tile-gap:0.75rem] pt-2">
              {results.map((res) => (
                <div key={res.mode} className="flex flex-col rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs gap-2">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-1.5 font-mono text-[11px]">
                    <span className="font-semibold text-cyan-300 uppercase">{res.mode}</span>
                    <span className="text-slate-500">{t('compare_time')} {res.duration_ms}ms</span>
                  </div>
                  {res.thought && (
                    <div className="p-2 rounded bg-slate-900/80 text-slate-400 italic text-[11px] max-h-24 overflow-y-auto">
                      {res.thought}
                    </div>
                  )}
                  <div className="overflow-y-auto max-h-72 leading-relaxed text-slate-200">
                    <Markdown source={res.content} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
