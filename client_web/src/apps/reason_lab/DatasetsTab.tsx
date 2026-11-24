import React, { useRef, useState } from 'react';
import { Btn, Empty, Field, List, Panel, Pill, Row, Stat, StatRow, inputClass } from '../shared/kit';
import { exportDataset, inspectDataset, loadDataset, loadTemplate, removeDataset, saveDataset } from './api';
import { ScenarioEditor } from './ScenarioEditor';
import type { Scenario, Summary } from './types';
import type { LabModel } from './useLab';

const SLUG = /^[a-z0-9][a-z0-9_]{2,39}$/;
const MAX_FILE = 4 * 1024 * 1024;
const blank = (): Scenario => ({ id: '', category: 'simple', expected: { intent: '', effects: ['read'] }, external_content: null, texts: { it: '' } });

function scenariosFrom(value: unknown): Scenario[] {
  const list = Array.isArray(value) ? value : (value as { scenarios?: unknown })?.scenarios;
  if (!Array.isArray(list)) throw new Error('dataset_format');
  return list as Scenario[];
}

export function DatasetsTab({ model: m }: { model: LabModel }) {
  const { t } = m;
  const [id, setId] = useState('');
  const [name, setName] = useState('');
  const [scenarios, setScenarios] = useState<Scenario[] | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [raw, setRaw] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const file = useRef<HTMLInputElement>(null);
  const ready = scenarios !== null && SLUG.test(id) && name.trim() !== '';

  const edit = (next: Scenario[]) => { setScenarios(next); setSummary(null); setProblem(null); };
  const open = async (target: string) => {
    const loaded = await m.run(() => loadDataset(target));
    if (loaded) { setId(loaded.id); setName(loaded.name); edit(loaded.scenarios); setSummary((loaded.summary as Summary) ?? null); setRaw(null); }
  };
  const fromTemplate = async () => {
    const loaded = await m.run(() => loadTemplate());
    if (loaded) { setId(''); setName(''); edit(loaded.scenarios); setRaw(null); }
  };
  const importFile = async (selected: File | undefined) => {
    if (!selected) return;
    try {
      if (selected.size > MAX_FILE) throw new Error('too_large');
      edit(scenariosFrom(JSON.parse(await selected.text())));
      setName(previous => previous || selected.name.replace(/\.json$/i, '').slice(0, 80));
      setRaw(null);
    } catch {
      setProblem(t('import_invalid'));
    }
    if (file.current) file.current.value = '';
  };
  const check = async () => {
    if (!scenarios) return;
    const result = await m.run(() => inspectDataset(name || 'x', scenarios));
    if (result) { setSummary(result); setProblem(null); } else setProblem(t('dataset_invalid'));
  };
  const save = async () => {
    if (!scenarios) return;
    const saved = await m.run(() => saveDataset(id, name.trim(), scenarios));
    if (saved) { m.datasetsResource.reload(); setProblem(null); m.setNotice(t('dataset_saved')); } else setProblem(t('dataset_invalid'));
  };
  const applyRaw = () => {
    try { edit(scenariosFrom(JSON.parse(raw ?? ''))); setRaw(null); } catch { setProblem(t('import_invalid')); }
  };

  return (
    <div className="flex flex-col gap-4">
      <Panel title={t('datasets')} actions={<div className="flex gap-2"><Btn onClick={() => void fromTemplate()}>{t('from_template')}</Btn><Btn onClick={() => file.current?.click()}>{t('import_file')}</Btn></div>}>
        <input ref={file} type="file" accept="application/json,.json" hidden onChange={event => void importFile(event.target.files?.[0])} />
        {m.datasets.length === 0 ? <Empty>{t('no_datasets')}</Empty> : (
          <List>
            {m.datasets.map(item => (
              <Row key={item.id} actions={<>
                <Btn onClick={() => void open(item.id)}>{t('edit')}</Btn>
                <Btn onClick={() => void m.run(() => exportDataset(item.id))}>{t('export')}</Btn>
                <Btn tone="rose" onClick={() => void m.run(() => removeDataset(item.id)).then(() => m.datasetsResource.reload())}>{t('delete')}</Btn>
              </>}>
                <strong>{item.name}</strong> <Pill>{item.id}</Pill>
                <div className="text-xs text-on-surface-variant">{t('dataset_counts', { scenarios: item.summary.scenarios ?? 0, cases: item.summary.cases ?? 0 })} · {m.time(item.updated)}</div>
              </Row>
            ))}
          </List>
        )}
      </Panel>
      {problem && <p role="alert" className="rounded-2xl bg-error-container p-3 text-sm text-on-error-container">{problem}</p>}
      {scenarios && (
        <Panel title={t('editor')} actions={<div className="flex gap-2"><Btn onClick={() => setRaw(raw === null ? JSON.stringify(scenarios, null, 1) : null)}>{t(raw === null ? 'raw_mode' : 'form_mode')}</Btn><Btn onClick={() => edit([...scenarios, blank()])}>{t('add_scenario')}</Btn></div>}>
          <div className="mb-3 grid gap-3 cq-lg:grid-cols-2">
            <Field label={t('dataset_id')}><input className={inputClass} value={id} maxLength={40} onChange={event => setId(event.target.value.toLowerCase())} /></Field>
            <Field label={t('dataset_name')}><input className={inputClass} value={name} maxLength={80} onChange={event => setName(event.target.value)} /></Field>
          </div>
          {raw !== null ? (
            <div className="flex flex-col gap-2">
              <textarea aria-label={t('raw_mode')} className={`${inputClass} font-mono`} rows={16} value={raw} onChange={event => setRaw(event.target.value)} />
              <div><Btn onClick={applyRaw}>{t('apply')}</Btn></div>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {scenarios.map((scenario, index) => (
                <ScenarioEditor key={index} scenario={scenario} t={t} onChange={next => edit(scenarios.map((item, position) => (position === index ? next : item)))} onRemove={() => edit(scenarios.filter((_, position) => position !== index))} />
              ))}
            </div>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            <Btn onClick={() => void check()} busy={m.busy}>{t('check')}</Btn>
            <Btn tone="emerald" onClick={() => void save()} busy={m.busy} disabled={!ready}>{t('save')}</Btn>
          </div>
          {summary && (
            <div className="mt-3"><StatRow>
              <Stat label={t('scenarios')} value={summary.scenarios ?? 0} />
              <Stat label={t('cases')} value={summary.cases ?? 0} />
              {Object.entries(summary.by_language ?? {}).map(([code, count]) => <Stat key={code} label={code} value={count} tone="purple" />)}
            </StatRow></div>
          )}
        </Panel>
      )}
    </div>
  );
}
