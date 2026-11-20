import React, { useState } from 'react';
import { CheckCircle2, ExternalLink, KeyRound, Loader2, Play, Sparkles } from 'lucide-react';
import { Btn, Field, inputClass } from '../../shared/kit';
import { ElevenLabsSubscription, ElevenLabsVoice, EngineSettings } from '../types';

interface Props {
  readonly status: ElevenLabsSubscription | null;
  readonly voices: ElevenLabsVoice[];
  readonly settings: EngineSettings;
  readonly busy: boolean;
  readonly playingVoiceId: string | null;
  readonly onSaveKey: (key: string) => Promise<void>;
  readonly onSaveSettings: (settings: Partial<EngineSettings>) => Promise<void>;
  readonly onPreviewVoice: (voiceId: string, name: string) => void;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

export const ElevenLabsConfigPanel: React.FC<Props> = ({
  status,
  voices,
  settings,
  busy,
  playingVoiceId,
  onSaveKey,
  onSaveSettings,
  onPreviewVoice,
  t,
}) => {
  const [keyInput, setKeyInput] = useState('');
  const [showKeyField, setShowKeyField] = useState(false);
  const [keySubmitting, setKeySubmitting] = useState(false);

  const handleKeySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyInput.trim()) return;
    setKeySubmitting(true);
    try {
      await onSaveKey(keyInput.trim());
      setKeyInput('');
      setShowKeyField(false);
    } finally {
      setKeySubmitting(false);
    }
  };

  const isConfigured = status?.configured === true && status.status !== 'error';

  return (
    <div className="rounded-xl border border-purple-500/30 bg-purple-950/10 p-4 space-y-4">
      {/* HEADER & TIER BADGE */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-purple-500/20 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-purple-500/20 text-purple-300">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-purple-200">{t('elevenlabs_panel_title')}</h3>
            <p className="text-xs text-slate-400">{t('elevenlabs_panel_desc')}</p>
          </div>
        </div>

        {isConfigured ? (
          <div className="flex items-center gap-2">
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/40 font-mono font-semibold uppercase">
              {status.tier} Tier
            </span>
            <Btn tone="slate" onClick={() => setShowKeyField(!showKeyField)}>
              <KeyRound className="h-3 w-3 mr-1" />
              {t('change_key')}
            </Btn>
          </div>
        ) : (
          <Btn tone="purple" onClick={() => setShowKeyField(true)}>
            <KeyRound className="h-3 w-3 mr-1" />
            {t('configure_key')}
          </Btn>
        )}
      </div>

      {/* FORM INSERIMENTO CHIAVE API */}
      {(showKeyField || !isConfigured) && (
        <form onSubmit={handleKeySubmit} className="p-3 rounded-lg bg-slate-900/80 border border-slate-700 space-y-2">
          <label className="block text-xs font-semibold text-slate-300">
            {t('elevenlabs_key_label')}
          </label>
          <div className="flex gap-2">
            <input
              type="password"
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              placeholder="sk_..."
              className={`${inputClass} flex-1 font-mono text-xs`}
            />
            <Btn tone="purple" busy={keySubmitting} onClick={handleKeySubmit as any}>
              {t('save_and_verify')}
            </Btn>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span>{t('key_stored_securely')}</span>
            <a
              href="https://elevenlabs.io"
              target="_blank"
              rel="noreferrer"
              className="text-purple-400 hover:text-purple-300 flex items-center gap-1 font-medium underline"
            >
              {t('get_free_key_link')}
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </form>
      )}

      {/* QUOTA MONITOR GAUGE */}
      {isConfigured && (
        <div className="p-3 rounded-lg bg-slate-900/60 border border-purple-500/20 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-300 flex items-center gap-1.5">
              <span>📊</span> {t('quota_usage_title')}
            </span>
            <span className="font-mono text-purple-300 font-bold">
              {status.character_count.toLocaleString()} / {status.character_limit.toLocaleString()} {t('characters')} ({status.percent_used}%)
            </span>
          </div>

          {/* Barra progresso */}
          <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden border border-slate-700">
            <div
              className={`h-2.5 rounded-full transition-all duration-500 ${
                status.percent_used > 85 ? 'bg-rose-500' : 'bg-gradient-to-r from-purple-500 to-cyan-400'
              }`}
              style={{ width: `${Math.min(100, status.percent_used)}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span>
              {t('quota_remaining', { count: status.remaining_characters.toLocaleString() })}
            </span>
            <span>
              {t('quota_reset_days', { days: status.next_reset_days })}
            </span>
          </div>
        </div>
      )}

      {/* SELETTORE VOCE ELEVENLABS */}
      {isConfigured && voices.length > 0 && (
        <div className="grid grid-cols-1 cq-sm:grid-cols-2 gap-3 pt-2">
          <Field label={t('select_eleven_voice')}>
            <div className="flex gap-2">
              <select
                className={`${inputClass} flex-1`}
                value={settings.elevenlabs_voice_id}
                onChange={(e) => onSaveSettings({ elevenlabs_voice_id: e.target.value })}
              >
                {voices.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} {v.accent ? `(${v.accent})` : ''} {v.category === 'cloned' ? '⭐ Cloned' : ''}
                  </option>
                ))}
              </select>
              <Btn
                tone="purple"
                busy={playingVoiceId === settings.elevenlabs_voice_id}
                onClick={() => {
                  const curr = voices.find((v) => v.id === settings.elevenlabs_voice_id);
                  onPreviewVoice(settings.elevenlabs_voice_id, curr?.name || 'ElevenLabs');
                }}
                title={t('preview')}
              >
                <Play className="h-3.5 w-3.5" />
              </Btn>
            </div>
          </Field>

          {/* SLIDERS STABILITA & SIMILARITA */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                <span>{t('stability')}</span>
                <span className="font-mono text-purple-300">{Math.round(settings.stability * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.05"
                value={settings.stability}
                onChange={(e) => onSaveSettings({ stability: parseFloat(e.target.value) })}
                className="w-full accent-purple-400 cursor-pointer"
              />
            </div>
            <div>
              <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                <span>{t('similarity')}</span>
                <span className="font-mono text-purple-300">{Math.round(settings.similarity_boost * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.05"
                value={settings.similarity_boost}
                onChange={(e) => onSaveSettings({ similarity_boost: parseFloat(e.target.value) })}
                className="w-full accent-purple-400 cursor-pointer"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
