import React, { useState } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { Field, inputClass } from '../shared/kit';
import { StudioVoice, previewVoice, StudioEQ, StudioFX } from './studioApi';
import { WaveformPlayer } from './WaveformPlayer';
import { Play, Sparkles } from 'lucide-react';

interface Props {
  voices: StudioVoice[];
  defaultVoiceId?: string;
  eq?: StudioEQ;
  fx?: StudioFX;
}

export const TestLaboratory: React.FC<Props> = ({ voices, defaultVoiceId, eq, fx }) => {
  const { t, lang } = useScopedI18n('core_apps/voice_studio');
  const [selectedVoice, setSelectedVoice] = useState(defaultVoiceId || (voices[0]?.id ?? ''));
  const [testText, setTestText] = useState(
    'Benvenuto nello Studio delle Voci di Nuxiva. Questo è un test in tempo reale con equalizzazione parametrica, de-esser e controllo dinamico.'
  );
  const [audioUrl, setAudioUrl] = useState<string>('');
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');

  const quickSamples = [
    { label: 'Saluto & Presentazione', text: 'Ciao! Sono la voce personalizzata creata con lo Studio di Nuxiva.' },
    { label: 'Notifica Domotica', text: 'Attenzione: la lavatrice ha terminato il ciclo e il cancello è stato chiuso.' },
    { label: 'Lettura Notizie', text: 'Le previsioni per la giornata indicano cielo sereno con temperature primaverili.' },
    { label: 'Test Sibilanti (De-Esser)', text: 'Sette scettri scintillanti scivolavano sopra il sassoso sentiero.' },
  ];

  const generateTest = async () => {
    if (!testText.trim()) return;
    setGenerating(true);
    setError('');
    try {
      const blob = await previewVoice(selectedVoice, lang, {
        text: testText.trim(),
        eq,
        fx,
      });
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      setAudioUrl(URL.createObjectURL(blob));
    } catch (err: any) {
      setError(err?.message || 'Errore durante la generazione del test vocale');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-cyan-500/30 pb-4">
        <h4 className="flex items-center gap-2 text-base font-bold text-white">
          <Sparkles className="h-5 w-5 text-cyan-400" aria-hidden="true" />
          {t('test_lab_title')}
        </h4>
        <p className="text-xs text-slate-300">{t('test_lab_subtitle')}</p>
      </div>

      {error && (
        <p role="alert" className="rounded-xl border border-rose-500/40 bg-rose-500/20 p-4 text-xs font-semibold text-rose-200">
          {error}
        </p>
      )}

      {/* Selezione Voce e Prompt Rapidi */}
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label={t('voice_to_test')}>
          <select
            className={inputClass}
            value={selectedVoice}
            aria-label={t('voice_to_test')}
            onChange={(e) => setSelectedVoice(e.target.value)}
          >
            {voices.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name} ({v.language.toUpperCase()})
              </option>
            ))}
          </select>
        </Field>

        <div>
          <label className="mb-2 block text-xs font-bold text-slate-200">
            {t('quick_samples')}:
          </label>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Frasi di test preconfigurate">
            {quickSamples.map((s, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setTestText(s.text)}
                className="rounded-xl border border-slate-600 bg-slate-800 px-3.5 py-1.5 text-xs font-bold text-white transition hover:border-cyan-400 hover:bg-cyan-500 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 shadow-sm"
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Area Testo di Prova */}
      <Field label={t('test_text')}>
        <textarea
          rows={3}
          className={`${inputClass} resize-none`}
          value={testText}
          maxLength={500}
          aria-label={t('test_text')}
          onChange={(e) => setTestText(e.target.value)}
          placeholder="Digita qui il testo da sintetizzare per ascoltare il risultato..."
        />
        <div className="mt-1.5 flex justify-between text-xs font-medium text-slate-300">
          <span>{t('max_chars_hint')}</span>
          <span>{testText.length} / 500</span>
        </div>
      </Field>

      {/* Pulsante Generazione */}
      <div className="flex justify-end">
        <button
          type="button"
          disabled={generating || !testText.trim()}
          onClick={generateTest}
          className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 px-5 py-2.5 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-500/25 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Play className="h-4 w-4 fill-slate-950" aria-hidden="true" />
          {t('generate_test_audio')}
        </button>
      </div>

      {/* Player Forma d'Onda */}
      {audioUrl && (
        <div className="pt-2">
          <WaveformPlayer
            src={audioUrl}
            title={`${t('test_result')}: ${voices.find((v) => v.id === selectedVoice)?.name ?? selectedVoice}`}
          />
        </div>
      )}
    </div>
  );
};
