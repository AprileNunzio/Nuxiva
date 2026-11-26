import React, { useEffect, useState } from 'react';
import { Btn, Empty, Field, Panel, inputClass } from '../shared/kit';
import { saveConfig } from './api';
import type { Config, Gate } from './types';
import type { EngineModel } from './useEngine';

type Limits = Record<string, readonly [number, number]>;
const ENGINE: Limits = { retrieve_limit: [1, 24], max_corrections: [0, 3], cache_capacity: [1, 100000], understand_threshold_bps: [0, 10000] };
const GATE: Limits = { min_days: [1, 30], min_samples: [1, 1000000], min_agreement_bps: [0, 10000], max_invalid_bps: [0, 10000], max_wrong_action: [0, 1000] };
const HOUR_MS = 3600000;

function clamp(value: number, [low, high]: readonly [number, number]) {
  return Number.isFinite(value) ? Math.min(high, Math.max(low, Math.round(value))) : low;
}

export function SettingsTab({ model: m }: { model: EngineModel }) {
  const { t } = m;
  const loaded = m.status?.config;
  const [form, setForm] = useState<Config | null>(loaded ?? null);
  useEffect(() => setForm(previous => previous ?? loaded ?? null), [loaded]);
  if (!m.status?.native || !form) return <Empty>{m.status && !m.status.native ? t('native_missing') : t('loading')}</Empty>;
  const setEngine = (key: string, value: number) => setForm({ ...form, [key]: clamp(value, ENGINE[key]) });
  const setGate = (key: string, value: number) => setForm({ ...form, gate: { ...form.gate, [key]: clamp(value, GATE[key]) } as Gate });
  const hours = Math.round(form.cache_ttl_ms / HOUR_MS);
  const submit = () => void m.run(() => saveConfig(form)).then(() => m.statusResource.reload());
  return (
    <form className="flex flex-col gap-4" onSubmit={event => { event.preventDefault(); submit(); }}>
      <Panel title={t('settings_engine')}>
        <div className="grid gap-3 cq-lg:grid-cols-2">
          {Object.entries(ENGINE).map(([key, [low, high]]) => (
            <Field key={key} label={t(`cfg_${key}`)}>
              <input className={inputClass} type="number" min={low} max={high} value={form[key as keyof Config] as number} onChange={event => setEngine(key, Number(event.target.value))} />
            </Field>
          ))}
          <Field label={t('cfg_cache_ttl_hours')}>
            <input className={inputClass} type="number" min={1} max={720} value={hours} onChange={event => setForm({ ...form, cache_ttl_ms: clamp(Number(event.target.value), [1, 720]) * HOUR_MS })} />
          </Field>
        </div>
      </Panel>
      <Panel title={t('settings_gate')}>
        <p className="mb-3 text-xs text-on-surface-variant">{t('settings_gate_hint')}</p>
        <div className="grid gap-3 cq-lg:grid-cols-2">
          {Object.entries(GATE).map(([key, [low, high]]) => (
            <Field key={key} label={t(`cfg_${key}`)}>
              <input className={inputClass} type="number" min={low} max={high} value={form.gate[key as keyof Gate]} onChange={event => setGate(key, Number(event.target.value))} />
            </Field>
          ))}
        </div>
      </Panel>
      <div><Btn type="submit" busy={m.busy} tone="emerald">{t('save')}</Btn></div>
    </form>
  );
}
