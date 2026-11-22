import React, { useCallback, useEffect, useState } from 'react';
import { useStudioI18n } from '../scope';
import * as api from '../api';
import type { ModelMode } from '../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  projectId: string | null;
  activePresetId: string | null;
  onSelect: (presetId: string | null) => void;
  onChanged: () => void;
}

const MODES: ModelMode[] = ['fast', 'reasoning', 'creative', 'code'];

export const PresetsModal: React.FC<Props> = ({ isOpen, onClose, projectId, activePresetId, onSelect, onChanged }) => {
  const { t } = useStudioI18n();
  const [presets, setPresets] = useState<api.Preset[]>([]);
  const [name, setName] = useState('');
  const [prompt, setPrompt] = useState('');
  const [mode, setMode] = useState<ModelMode>('reasoning');
  const [scoped, setScoped] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      setPresets(await api.fetchPresets(projectId));
    } catch (e) {
      setError((e as Error).message);
    }
  }, [projectId]);

  useEffect(() => {
    if (isOpen) {
      setError('');
      void load();
    }
  }, [isOpen, load]);

  if (!isOpen) return null;

  const create = async () => {
    if (!name.trim()) return;
    try {
      await api.createPreset({
        name: name.trim(),
        description: '',
        system_prompt: prompt,
        model_mode: mode,
        project_id: scoped ? projectId : null,
      });
      setName('');
      setPrompt('');
      await load();
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose} role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        className="w-[min(40rem,94vw)] max-h-[85vh] flex flex-col rounded-2xl border border-white/10 bg-slate-900/90 backdrop-blur-xl shadow-[0_0_60px_-15px_rgba(0,240,255,0.35)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/10">
          <div className="text-sm font-semibold text-slate-100">🎭 {t('preset_title')}</div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-100" aria-label={t('close')}>
            ✕
          </button>
        </div>
        <div className="p-4 flex flex-col gap-3 overflow-y-auto">
          <p className="text-xs text-slate-400">{t('preset_desc')}</p>
          <ul className="flex flex-col gap-1.5">
            <li>
              <button
                type="button"
                onClick={() => onSelect(null)}
                className={`w-full text-left rounded-xl border px-3 py-2 text-xs ${
                  activePresetId === null ? 'border-cyan-500/60 bg-cyan-500/10 text-cyan-200' : 'border-white/10 text-slate-300'
                }`}
              >
                {t('preset_none')}
              </button>
            </li>
            {presets.map((p) => (
              <li key={p.id} className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => onSelect(p.id)}
                  className={`flex-1 text-left rounded-xl border px-3 py-2 text-xs truncate ${
                    activePresetId === p.id ? 'border-cyan-500/60 bg-cyan-500/10 text-cyan-200' : 'border-white/10 text-slate-300'
                  }`}
                >
                  {p.name} <span className="text-slate-500">· {p.model_mode}{p.project_id ? ` · ${t('preset_project')}` : ''}</span>
                </button>
                <button
                  type="button"
                  className="text-slate-500 hover:text-red-400 text-xs"
                  onClick={async () => {
                    await api.deletePreset(p.id).catch((e) => setError((e as Error).message));
                    if (activePresetId === p.id) onSelect(null);
                    await load();
                    onChanged();
                  }}
                >
                  🗑
                </button>
              </li>
            ))}
          </ul>

          <div className="flex flex-col gap-2 rounded-xl border border-white/10 p-3">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('preset_name')}
              className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white placeholder:text-slate-500"
            />
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={4}
              placeholder={t('preset_prompt')}
              className="px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white placeholder:text-slate-500 resize-y"
            />
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-300">
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as ModelMode)}
                className="px-2 py-1 rounded-lg bg-slate-950 border border-slate-700"
              >
                {MODES.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
              {projectId && (
                <label className="flex items-center gap-1">
                  <input type="checkbox" checked={scoped} onChange={(e) => setScoped(e.target.checked)} />
                  {t('preset_only_project')}
                </label>
              )}
              <button
                type="button"
                disabled={!name.trim()}
                onClick={() => void create()}
                className="ml-auto px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 text-white font-medium disabled:opacity-40"
              >
                {t('preset_create')}
              </button>
            </div>
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
        </div>
      </div>
    </div>
  );
};
