import React, { FormEvent, useState } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { Btn, Field, inputClass } from '../../core_apps/shared/kit';
import { StudioStatus, cloneVoice, designVoice } from './studioApi';

interface Props { status: StudioStatus; busy: boolean; run: (task: () => Promise<unknown>) => Promise<boolean>; }

export const StudioCreator: React.FC<Props> = ({ status, busy, run }) => {
  const { t, lang } = useScopedI18n('features/voice_studio');
  const [mode, setMode] = useState<'design' | 'clone'>('design');
  const [name, setName] = useState('');
  const [language, setLanguage] = useState<string>(lang);
  const [choices, setChoices] = useState<Record<string, string>>({});
  const [file, setFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [invalid, setInvalid] = useState(false);
  const sentence = (status.sentences[language] ?? status.sentences.en ?? '').replace('{name}', name.trim() || '…');
  const create = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim() || (mode === 'clone' && (!file || !consent))) return;
    const ok = await run(() => mode === 'design' ? designVoice({ ...choices, name: name.trim(), language }) : cloneVoice(name.trim(), language, file!));
    if (ok) { setName(''); setFile(null); setConsent(false); }
  };
  return (
    <form onSubmit={create} className="mt-4 space-y-3 border-t border-slate-700 pt-4">
      <div className="flex flex-wrap gap-2">
        {(['design', 'clone'] as const).map((value) => <Btn key={value} tone={mode === value ? 'cyan' : 'slate'} onClick={() => setMode(value)}>{t(value)}</Btn>)}
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label={t('name')}><input className={inputClass} value={name} maxLength={40} required onChange={(event) => setName(event.target.value)} /></Field>
        <Field label={t('language')}><select className={inputClass} value={language} onChange={(event) => setLanguage(event.target.value)}>{['it', 'en', 'fr', 'es', 'de', 'pt'].map((value) => <option key={value} value={value}>{value.toUpperCase()}</option>)}</select></Field>
      </div>
      {mode === 'design' ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {Object.entries(status.choices).map(([key, options]) => <Field key={key} label={t(key)}>
            <select className={inputClass} value={choices[key] ?? ''} onChange={(event) => setChoices((current) => ({ ...current, [key]: event.target.value }))}>
              <option value="">{t('automatic')}</option>
              {options.filter((option) => option.value).map((option) => <option key={option.value} value={option.value}>{option.icon} {t(`choice_${option.value.replace(/ /g, '_')}`)}</option>)}
            </select>
          </Field>)}
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-slate-400">{t('clone_hint')}</p>
          <blockquote className="rounded-xl bg-slate-950 p-3 text-sm text-cyan-100">{sentence}</blockquote>
          <label className="block text-xs text-slate-300">{t('audio_file')}<input className="mt-2 block w-full text-xs" type="file" accept="audio/*,video/webm" onChange={(event) => {
            const selected = event.target.files?.[0] ?? null;
            const valid = selected !== null && selected.size >= 20000 && selected.size <= 25 * 1024 * 1024;
            setInvalid(selected !== null && !valid); setFile(valid ? selected : null);
          }} /></label>
          {invalid && <p role="alert" className="text-xs text-rose-200">{t('audio_invalid')}</p>}
          <label className="flex items-start gap-2 text-xs text-slate-300"><input type="checkbox" className="mt-0.5" checked={consent} onChange={(event) => setConsent(event.target.checked)} />{t('consent')}</label>
        </div>
      )}
      <Btn type="submit" busy={busy} disabled={!status.online || !name.trim() || (mode === 'clone' ? !file || !consent : !Object.values(choices).some(Boolean))}>{t('create')}</Btn>
    </form>
  );
};
