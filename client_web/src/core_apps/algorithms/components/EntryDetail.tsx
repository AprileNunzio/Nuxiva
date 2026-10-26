import React, { useEffect, useState } from 'react';
import { FlaskConical, Save, Trash2 } from 'lucide-react';
import { Btn, Pill, Toggle, inputClass, panelClass } from '../../shared/kit';
import { useAction } from '../../shared/useResource';
import { fetchAlgorithmCode, removeAlgorithm, saveAlgorithmCode, setEnabled, testAlgorithm } from '../api';
import { AlgorithmTest, CatalogEntry } from '../types';

interface EntryDetailProps {
  readonly entry: CatalogEntry;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly onChanged: () => void;
  readonly onRemoved: () => void;
}

export const EntryDetail: React.FC<EntryDetailProps> = ({ entry, t, onChanged, onRemoved }) => {
  const { busy, run } = useAction(onChanged);
  const [probe, setProbe] = useState(entry.examples?.[0] ?? '');
  const [outcome, setOutcome] = useState<AlgorithmTest | null>(null);
  const [code, setCode] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [problem, setProblem] = useState('');
  const isSkill = entry.kind === 'skill';

  useEffect(() => {
    setProbe(entry.examples?.[0] ?? '');
    setOutcome(null);
    setCode(null);
    setProblem('');
    if (!isSkill) {
      return undefined;
    }
    let live = true;
    fetchAlgorithmCode(entry.ref)
      .then((value) => {
        if (live) {
          setCode(value);
          setDraft(value);
        }
      })
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [entry.key, entry.ref, entry.examples, isSkill]);

  const test = async () => {
    const out = await run(() => testAlgorithm(entry.ref, probe.trim()), 'algorithms_test_failed');
    setOutcome(out);
  };

  const saveCode = async () => {
    setProblem('');
    try {
      await saveAlgorithmCode(entry.ref, draft);
      setCode(draft);
      onChanged();
    } catch (cause) {
      setProblem(cause instanceof Error ? cause.message : t('save_failed'));
    }
  };

  const remove = async () => {
    if ((await run(() => removeAlgorithm(entry.ref), 'algorithms_delete_failed')) !== null) {
      onRemoved();
    }
  };

  return (
    <aside className={`${panelClass} flex flex-col gap-4`} aria-label={entry.name}>
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="break-words text-base font-bold text-slate-900">{entry.name}</h2>
          <div className="mt-1 flex flex-wrap gap-1.5">
            <Pill tone="purple">{t(`kind_${entry.kind}`)}</Pill>
            <Pill>{entry.group}</Pill>
            <Pill tone={entry.source === 'system' ? 'slate' : 'cyan'}>{t(`source_${entry.source}`)}</Pill>
          </div>
        </div>
        {entry.manageable ? <Toggle checked={entry.enabled} disabled={busy} label={t('enabled')} onChange={(value) => void run(() => setEnabled(entry.ref, value), 'algorithms_toggle_failed')} /> : <Pill tone={entry.enabled ? 'emerald' : 'slate'}>{entry.enabled ? t('on') : t('off')}</Pill>}
      </header>
      <p className="text-sm text-slate-700">{entry.description || t('no_description')}</p>

      {entry.kind === 'tool' ? (
        <dl className="grid gap-2 text-xs text-slate-600">
          <div><dt className="font-semibold text-slate-700">{t('tool_arguments')}</dt><dd>{entry.arguments?.length ? entry.arguments.join(', ') : '—'}</dd></div>
          <div><dt className="font-semibold text-slate-700">{t('tool_confirm')}</dt><dd>{entry.confirm ? t('yes') : t('no')}</dd></div>
        </dl>
      ) : null}
      {entry.kind === 'connector' ? <p className="text-xs text-slate-600">{entry.declares_requests ? t('connector_declares') : t('connector_legacy')}</p> : null}

      {isSkill ? (
        <>
          <p className="text-xs text-slate-500">{t('usage', { uses: entry.uses ?? 0, fails: entry.fails ?? 0 })}</p>
          {entry.patterns?.length ? (
            <div>
              <h3 className="mb-1 text-xs font-semibold text-slate-700">{t('patterns')}</h3>
              <ul className="flex flex-col gap-1">
                {entry.patterns.map((pattern) => (
                  <li key={pattern}><code className="break-all rounded bg-white px-2 py-0.5 text-[11px] text-blue-800">{pattern}</code></li>
                ))}
              </ul>
            </div>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <input className={`${inputClass} min-w-0 flex-1`} value={probe} maxLength={500} aria-label={t('try_label')} onChange={(event) => setProbe(event.target.value)} />
            <Btn busy={busy} disabled={!probe.trim()} onClick={() => void test()}>
              <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />
              {t('try')}
            </Btn>
          </div>
          {outcome ? (
            <p className={`text-xs ${outcome.ok ? 'text-emerald-700' : 'text-rose-700'}`}>
              {outcome.ok ? outcome.speech ?? String(outcome.result ?? '') : outcome.error} · {outcome.total_ms} ms · {outcome.matches ? t('matches') : t('no_match')}
            </p>
          ) : null}
          {code !== null ? (
            <div className="flex flex-col gap-2">
              <h3 className="text-xs font-semibold text-slate-700">{t('code')}</h3>
              <textarea
                className={`${inputClass} h-64 font-mono text-xs`}
                spellCheck={false}
                readOnly={!entry.editable}
                value={draft}
                aria-label={t('code')}
                onChange={(event) => setDraft(event.target.value)}
              />
              {problem ? <p role="alert" className="text-xs text-rose-700">{problem}</p> : null}
              {entry.editable ? (
                <div className="flex flex-wrap gap-2">
                  <Btn tone="emerald" busy={busy} disabled={draft === code} onClick={() => void saveCode()}>
                    <Save className="h-3.5 w-3.5" aria-hidden="true" />
                    {t('save_code')}
                  </Btn>
                  <Btn tone="rose" busy={busy} onClick={() => void remove()}>
                    <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    {t('delete')}
                  </Btn>
                </div>
              ) : (
                <p className="text-xs text-slate-500">{t('system_readonly')}</p>
              )}
            </div>
          ) : null}
        </>
      ) : null}
    </aside>
  );
};
