import React, { useState } from 'react';
import { Hammer, Sparkles } from 'lucide-react';
import { Btn, Field, Panel, inputClass } from '../../shared/kit';
import { useAction } from '../../shared/useResource';
import { createAlgorithm, generateAlgorithm } from '../api';
import { AlgorithmDraft } from '../types';

interface CreateTabProps {
  readonly categories: Readonly<Record<string, string>>;
  readonly canGenerate: boolean;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly onCreated: (key: string) => void;
}

const TEMPLATE = `def run(text: str) -> dict:
    return {"ok": False, "error": "da completare"}
`;

const lines = (value: string) => value.split('\n').map((line) => line.trim()).filter(Boolean);

export const CreateTab: React.FC<CreateTabProps> = ({ categories, canGenerate, t, onCreated }) => {
  const [description, setDescription] = useState('');
  const [name, setName] = useState('');
  const [category, setCategory] = useState('altro');
  const [summary, setSummary] = useState('');
  const [patterns, setPatterns] = useState('');
  const [examples, setExamples] = useState('');
  const [probe, setProbe] = useState('');
  const [code, setCode] = useState(TEMPLATE);
  const [problem, setProblem] = useState('');
  const [working, setWorking] = useState(false);
  const { run } = useAction();

  const guarded = async (task: () => Promise<{ key: string }>) => {
    setProblem('');
    setWorking(true);
    try {
      onCreated((await task()).key);
    } catch (cause) {
      setProblem(cause instanceof Error && cause.message !== 'request_failed' ? cause.message : t('create_failed'));
    } finally {
      setWorking(false);
    }
  };

  const draft = (): AlgorithmDraft => ({ name, category, description: summary, patterns: lines(patterns), examples: lines(examples), code, probe });

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Panel title={t('generate_title')} icon={<Sparkles className="h-4 w-4 text-amber-300" aria-hidden="true" />}>
        <p className="mb-3 text-xs text-slate-400">{canGenerate ? t('generate_hint') : t('generate_disabled')}</p>
        <textarea className={`${inputClass} h-32`} value={description} maxLength={500} aria-label={t('generate_title')} placeholder={t('generate_placeholder')} onChange={(event) => setDescription(event.target.value)} />
        <div className="mt-3">
          <Btn tone="amber" busy={working} disabled={!canGenerate || !description.trim()} onClick={() => void run(() => guarded(() => generateAlgorithm(description.trim())))}>
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            {t('generate_action')}
          </Btn>
        </div>
      </Panel>

      <Panel title={t('manual_title')} icon={<Hammer className="h-4 w-4 text-cyan-300" aria-hidden="true" />}>
        <div className="grid gap-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={t('field_name')}>
              <input className={inputClass} value={name} maxLength={60} onChange={(event) => setName(event.target.value)} />
            </Field>
            <Field label={t('category')}>
              <select className={inputClass} value={category} onChange={(event) => setCategory(event.target.value)}>
                {Object.entries(categories).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </Field>
          </div>
          <Field label={t('field_description')}>
            <input className={inputClass} value={summary} maxLength={200} onChange={(event) => setSummary(event.target.value)} />
          </Field>
          <Field label={t('field_patterns')}>
            <textarea className={`${inputClass} h-20 font-mono text-xs`} value={patterns} spellCheck={false} onChange={(event) => setPatterns(event.target.value)} />
          </Field>
          <Field label={t('field_examples')}>
            <textarea className={`${inputClass} h-16`} value={examples} onChange={(event) => setExamples(event.target.value)} />
          </Field>
          <Field label={t('field_probe')}>
            <input className={inputClass} value={probe} maxLength={500} onChange={(event) => setProbe(event.target.value)} />
          </Field>
          <Field label={t('code')}>
            <textarea className={`${inputClass} h-56 font-mono text-xs`} value={code} spellCheck={false} onChange={(event) => setCode(event.target.value)} />
          </Field>
          <p className="text-[11px] text-slate-500">{t('manual_rules')}</p>
          {problem ? <p role="alert" className="text-xs text-rose-300">{problem}</p> : null}
          <div>
            <Btn tone="emerald" busy={working} disabled={!name.trim() || !patterns.trim() || !probe.trim()} onClick={() => void run(() => guarded(() => createAlgorithm(draft())))}>
              {t('manual_action')}
            </Btn>
          </div>
        </div>
      </Panel>
    </div>
  );
};
