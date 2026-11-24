import React, { useMemo, useState } from 'react';
import { Btn, Empty, Field, List, Panel, Pill, Row, inputClass } from '../shared/kit';
import { cancelRun, removeRun, startRun } from './api';
import { BACKENDS, CATEGORIES, FINAL_STATES } from './types';
import type { Backend, Category, Run, RunSpec } from './types';
import type { LabModel } from './useLab';

const TONES: Record<string, 'cyan' | 'emerald' | 'amber' | 'rose' | 'slate'> = {
  queued: 'slate', running: 'cyan', completed: 'emerald', cancelled: 'amber', failed: 'rose', interrupted: 'amber',
};

function toggle<T>(list: T[], item: T): T[] {
  return list.includes(item) ? list.filter(value => value !== item) : [...list, item];
}

function Progress({ run }: { run: Run }) {
  const percent = run.total ? Math.round((run.done / run.total) * 100) : 0;
  return (
    <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-surface-container-highest" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
      <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${percent}%` }} />
    </div>
  );
}

export function RunsTab({ model: m }: { model: LabModel }) {
  const { t } = m;
  const [profileId, setProfileId] = useState('');
  const [dataset, setDataset] = useState('');
  const [backend, setBackend] = useState<Backend>('ollama');
  const [baseUrl, setBaseUrl] = useState('http://127.0.0.1:11434');
  const [modelName, setModelName] = useState('');
  const [key, setKey] = useState('');
  const [label, setLabel] = useState('');
  const [languages, setLanguages] = useState<string[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [limit, setLimit] = useState(6000);
  const [concurrency, setConcurrency] = useState(1);
  const [timeoutSeconds, setTimeoutSeconds] = useState(60);
  const chosen = m.datasets.find(item => item.id === dataset);
  const available = useMemo(() => Object.keys(chosen?.summary.by_language ?? {}).sort(), [chosen]);
  const ready = m.status?.native !== false;
  const canStart = ready && dataset !== '' && modelName.trim() !== '' && baseUrl.trim() !== '';

  const applyProfile = (id: string) => {
    setProfileId(id);
    const profile = m.profiles.find(item => item.id === id);
    if (!profile) return;
    setBackend(profile.backend);
    setBaseUrl(profile.base_url);
    setModelName(profile.model);
    setTimeoutSeconds(profile.timeout_seconds);
  };

  const submit = async () => {
    const spec: RunSpec = {
      dataset, backend, base_url: baseUrl.trim(), model: modelName.trim(), key: key || null, label: label.trim(), languages, categories,
      limit, concurrency, timeout_seconds: timeoutSeconds,
    };
    const started = await m.run(() => startRun(spec));
    setKey('');
    if (started) {
      m.runsResource.reload();
      m.setNotice(t('run_started'));
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {!ready && <p role="alert" className="rounded-2xl bg-error-container p-3 text-sm text-on-error-container">{t('native_missing')}</p>}
      <Panel title={t('new_run')}>
        <form className="grid gap-3 cq-lg:grid-cols-2" onSubmit={event => { event.preventDefault(); if (canStart) void submit(); }}>
          <Field label={t('profile')}>
            <select className={inputClass} value={profileId} onChange={event => applyProfile(event.target.value)}>
              <option value="">{t('manual')}</option>
              {m.profiles.map(profile => <option key={profile.id} value={profile.id}>{profile.name}</option>)}
            </select>
          </Field>
          <Field label={t('dataset')}>
            <select className={inputClass} value={dataset} onChange={event => { setDataset(event.target.value); setLanguages([]); }}>
              <option value="">{t('choose')}</option>
              {m.datasets.map(item => <option key={item.id} value={item.id}>{item.name} ({item.summary.cases ?? 0})</option>)}
            </select>
          </Field>
          <Field label={t('backend')}>
            <select className={inputClass} value={backend} onChange={event => setBackend(event.target.value as Backend)}>
              {BACKENDS.map(item => <option key={item} value={item}>{t(`backend_${item}`)}</option>)}
            </select>
          </Field>
          <Field label={t('base_url')}>
            <input className={inputClass} value={baseUrl} maxLength={256} inputMode="url" autoComplete="off" onChange={event => setBaseUrl(event.target.value)} />
          </Field>
          <Field label={t('model')}>
            <input className={inputClass} value={modelName} maxLength={100} autoComplete="off" onChange={event => setModelName(event.target.value)} />
          </Field>
          <Field label={t('key')}>
            <input className={inputClass} type="password" value={key} maxLength={512} autoComplete="new-password" onChange={event => setKey(event.target.value)} />
            <span className="text-[11px] font-normal">{t('key_hint')}</span>
          </Field>
          <Field label={t('label')}>
            <input className={inputClass} value={label} maxLength={80} onChange={event => setLabel(event.target.value)} />
          </Field>
          <div className="grid grid-cols-3 gap-2">
            <Field label={t('limit')}>
              <input className={inputClass} type="number" min={1} max={m.status?.max_cases ?? 6000} value={limit} onChange={event => setLimit(Number(event.target.value) || 1)} />
            </Field>
            <Field label={t('concurrency')}>
              <input className={inputClass} type="number" min={1} max={m.status?.max_concurrency ?? 4} value={concurrency} onChange={event => setConcurrency(Number(event.target.value) || 1)} />
            </Field>
            <Field label={t('timeout')}>
              <input className={inputClass} type="number" min={5} max={300} value={timeoutSeconds} onChange={event => setTimeoutSeconds(Number(event.target.value) || 60)} />
            </Field>
          </div>
          <fieldset className="flex flex-wrap gap-2 text-xs">
            <legend className="mb-1 font-semibold text-on-surface-variant">{t('languages')}</legend>
            {available.length === 0 && <span>{t('all_languages')}</span>}
            {available.map(code => (
              <label key={code} className="flex items-center gap-1"><input type="checkbox" checked={languages.includes(code)} onChange={() => setLanguages(toggle(languages, code))} />{code}</label>
            ))}
          </fieldset>
          <fieldset className="flex flex-wrap gap-2 text-xs">
            <legend className="mb-1 font-semibold text-on-surface-variant">{t('categories')}</legend>
            {CATEGORIES.map(item => (
              <label key={item} className="flex items-center gap-1"><input type="checkbox" checked={categories.includes(item)} onChange={() => setCategories(toggle(categories, item))} />{t(`category_${item}`)}</label>
            ))}
          </fieldset>
          <div className="flex items-center gap-3 cq-lg:col-span-2">
            <Btn type="submit" busy={m.busy} disabled={!canStart} tone="emerald">{t('start')}</Btn>
            {m.notice && <span role="status" className="text-xs text-on-surface-variant">{m.notice}</span>}
          </div>
        </form>
      </Panel>
      <Panel title={t('runs')}>
        {m.runs.length === 0 ? <Empty>{t('no_runs')}</Empty> : (
          <List>
            {m.runs.map(item => {
              const active = !FINAL_STATES.includes(item.state);
              return (
                <Row key={item.id} actions={<>
                  <Btn onClick={() => m.openResults(item.id)}>{t('open')}</Btn>
                  {active && <Btn tone="amber" onClick={() => void m.run(() => cancelRun(item.id)).then(() => m.runsResource.reload())}>{t('cancel')}</Btn>}
                  <Btn tone="rose" onClick={() => void m.run(() => removeRun(item.id)).then(() => m.runsResource.reload())}>{t('delete')}</Btn>
                </>}>
                  <div className="flex flex-wrap items-center gap-2">
                    <strong>{item.label || item.model}</strong>
                    <Pill tone={TONES[item.state] ?? 'slate'}>{t(`state_${item.state}`)}</Pill>
                    {item.error && <Pill tone="rose">{t(`error_${item.error}`)}</Pill>}
                  </div>
                  <div className="text-xs text-on-surface-variant">{item.model} · {item.dataset_name} · {m.time(item.started)} · {item.done}/{item.total}</div>
                  <Progress run={item} />
                </Row>
              );
            })}
          </List>
        )}
      </Panel>
    </div>
  );
}
