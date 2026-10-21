import React, { FormEvent, useState } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { Field, inputClass } from '../shared/kit';
import { StudioStatus, designVoice } from './studioApi';
import { Wand2 } from 'lucide-react';

interface Props {
  status: StudioStatus;
  busy: boolean;
  run: (task: () => Promise<unknown>) => Promise<boolean>;
  onSuccess?: () => void;
}

export const StudioCreator: React.FC<Props> = ({ status, busy, run, onSuccess }) => {
  const { t, lang } = useScopedI18n('core_apps/voice_studio');
  const [name, setName] = useState('');
  const [language, setLanguage] = useState<string>(lang);
  const [choices, setChoices] = useState<Record<string, string>>({});

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return;
    const ok = await run(() => designVoice({ ...choices, name: name.trim(), language }));
    if (ok) {
      setName('');
      setChoices({});
      if (onSuccess) onSuccess();
    }
  };

  return (
    <form onSubmit={handleCreate} className="space-y-6">
      <div className="border-b border-cyan-500/30 pb-4">
        <h4 className="flex items-center gap-2 text-base font-bold text-white">
          <Wand2 className="h-5 w-5 text-cyan-400" aria-hidden="true" />
          {t('design')}
        </h4>
        <p className="text-xs text-slate-300">
          Personalizza timbro, genere, età e intonazione per generare un nuovo profilo vocale sintetico esclusivo.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t('name')}>
          <input
            className={inputClass}
            value={name}
            maxLength={40}
            required
            aria-required="true"
            placeholder="Es. Silvia Narratrice"
            onChange={(event) => setName(event.target.value)}
          />
        </Field>
        <Field label={t('language')}>
          <select
            className={inputClass}
            value={language}
            aria-label={t('language')}
            onChange={(event) => setLanguage(event.target.value)}
          >
            {['it', 'en', 'fr', 'es', 'de', 'pt'].map((value) => (
              <option key={value} value={value}>
                {value.toUpperCase()}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <div className="rounded-2xl border border-slate-700 bg-slate-900/90 p-5 shadow-lg">
        <span className="mb-3 block text-xs font-bold text-cyan-300">Caratteristiche Vocali:</span>
        <div className="grid gap-4 sm:grid-cols-2">
          {Object.entries(status.choices).map(([key, options]) => (
            <Field key={key} label={t(key)}>
              <select
                className={inputClass}
                value={choices[key] ?? ''}
                aria-label={t(key)}
                onChange={(event) =>
                  setChoices((current) => ({ ...current, [key]: event.target.value }))
                }
              >
                <option value="">{t('automatic')}</option>
                {options
                  .filter((option) => option.value)
                  .map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.icon} {t(`choice_${option.value.replace(/ /g, '_')}`)}
                    </option>
                  ))}
              </select>
            </Field>
          ))}
        </div>
      </div>

      <button
        type="submit"
        disabled={busy || !name.trim()}
        className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 px-5 py-2.5 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-500/25 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <Wand2 className="h-4 w-4" aria-hidden="true" />
        {t('create')}
      </button>
    </form>
  );
};
