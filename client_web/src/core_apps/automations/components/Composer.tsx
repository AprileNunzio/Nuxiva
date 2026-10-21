import React, { FormEvent, useState } from 'react';
import { Sparkles } from 'lucide-react';
import { Btn, Field, Panel, Pill, inputClass } from '../../shared/kit';
import { generate, saveAutomation } from '../api';
import { GeneratedAutomation } from '../types';

interface ComposerProps {
  readonly busy: boolean;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly run: <R>(task: () => Promise<R>, code?: string) => Promise<R | null>;
}

export const Composer: React.FC<ComposerProps> = ({ busy, t, run }) => {
  const [text, setText] = useState('');
  const [draft, setDraft] = useState<GeneratedAutomation | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (text.trim().length < 5) {
      return;
    }
    setDraft(await run(() => generate(text.trim()), 'automations_generate_failed'));
  };

  const save = async () => {
    if (draft && (await run(() => saveAutomation({ ...draft.automation, enabled: false }), 'automations_save_failed')) !== null) {
      setDraft(null);
      setText('');
    }
  };

  const name = typeof draft?.automation.name === 'string' ? draft.automation.name : '';

  return (
    <Panel title={t('compose_title')} icon={<Sparkles className="h-4 w-4 text-purple-300" aria-hidden="true" />}>
      <form onSubmit={submit} className="flex flex-col gap-3">
        <Field label={t('compose_label')}>
          <textarea className={`${inputClass} h-24`} value={text} maxLength={1000} onChange={(event) => setText(event.target.value)} placeholder={t('compose_placeholder')} />
        </Field>
        <Btn type="submit" busy={busy} disabled={text.trim().length < 5}>
          {t('compose_generate')}
        </Btn>
      </form>
      {draft ? (
        <div className="mt-4 flex flex-col gap-2 rounded-xl border border-slate-700 bg-slate-950/60 p-3">
          <div className="flex items-center justify-between gap-2">
            <b className="text-sm">{name}</b>
            <Pill tone={draft.errors.length ? 'rose' : 'emerald'}>{draft.errors.length ? t('draft_errors', { n: draft.errors.length }) : t('draft_valid')}</Pill>
          </div>
          {draft.errors.length ? <pre className="max-h-40 overflow-auto whitespace-pre-wrap text-[11px] text-rose-200">{JSON.stringify(draft.errors, null, 1)}</pre> : null}
          <pre className="max-h-56 overflow-auto whitespace-pre-wrap font-mono text-[11px] text-slate-300">{JSON.stringify(draft.automation, null, 1)}</pre>
          <Btn tone="emerald" busy={busy} disabled={draft.errors.length > 0} onClick={() => void save()}>
            {t('draft_save')}
          </Btn>
          <p className="text-[11px] text-slate-500">{t('draft_note')}</p>
        </div>
      ) : null}
    </Panel>
  );
};
