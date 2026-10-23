import React from 'react';
import { Lightbulb, Megaphone, Play, Siren, Square } from 'lucide-react';
import { Btn, Empty, Field, Panel, Pill, Toggle, inputClass } from '../../shared/kit';
import { saveSettings, setMode } from '../../shared/featureApi';
import { useAction, useResource } from '../../shared/useResource';
import type { FeatureRow } from '../../shared/featureTypes';
import { RedAlertLight, RedAlertStatus, redAlertLightsUrl, redAlertStatusUrl, stopRedAlert, testRedAlert } from './redAlertApi';

interface RedAlertSectionProps {
  readonly feature: FeatureRow;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly onChanged: () => void;
}

const DURATIONS = ['30', '60', '120', '300'];
const REPEATS = ['10', '25', '45', '90'];

export const RedAlertSection: React.FC<RedAlertSectionProps> = ({ feature, t, onChanged }) => {
  const status = useResource<RedAlertStatus>(redAlertStatusUrl, 3000);
  const lights = useResource<{ lights: readonly RedAlertLight[] }>(redAlertLightsUrl, 30000);
  const refresh = () => {
    status.reload();
    onChanged();
  };
  const { busy, run } = useAction(refresh);
  const value = (key: string, fallback: string) => feature.values[key] ?? fallback;
  const excluded = new Set(status.data?.excluded ?? []);
  const save = (values: Record<string, string>) => void run(() => saveSettings(feature.id, values), 'features_settings_failed');

  const toggleLight = (id: string) => {
    const next = new Set(excluded);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    save({ NUXIVA_REDALERT_EXCLUDE: [...next].join(',') });
  };

  const active = status.data?.active === true;

  return (
    <div className="flex flex-col gap-4">
      <Panel
        title={t('redalert_title')}
        icon={<Siren className="h-4 w-4 text-rose-700" aria-hidden="true" />}
        actions={<Pill tone={active ? 'rose' : feature.state.enabled ? 'emerald' : 'slate'}>{active ? t('redalert_active') : feature.state.enabled ? t('on') : t('off')}</Pill>}
      >
        <p className="mb-4 text-sm text-slate-600">{t('redalert_intro')}</p>
        {active && status.data?.message ? <p className="mb-3 rounded-xl border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-800">{status.data.message}</p> : null}
        <div className="flex flex-wrap items-center gap-2">
          <Btn tone="amber" busy={busy} disabled={!feature.state.enabled || active} onClick={() => void run(testRedAlert, 'redalert_test_failed')}>
            <Play className="h-3.5 w-3.5" aria-hidden="true" />
            {t('redalert_test')}
          </Btn>
          <Btn tone="rose" busy={busy} disabled={!active} onClick={() => void run(stopRedAlert, 'redalert_stop_failed')}>
            <Square className="h-3.5 w-3.5" aria-hidden="true" />
            {t('redalert_stop')}
          </Btn>
        </div>
      </Panel>

      <Panel title={t('redalert_behaviour')} icon={<Megaphone className="h-4 w-4 text-amber-700" aria-hidden="true" />}>
        <div className="grid gap-4 lg:grid-cols-2">
          <Field label={t('mode')}>
            <select className={inputClass} disabled={busy} value={feature.state.mode} onChange={(event) => void run(() => setMode(feature.id, event.target.value), 'features_mode_failed')}>
              <option value="auto">{t('mode_auto')}</option>
              <option value="1">{t('mode_on')}</option>
              <option value="0">{t('mode_off')}</option>
            </select>
          </Field>
          <Field label={t('redalert_duration')}>
            <select className={inputClass} disabled={busy} value={value('NUXIVA_REDALERT_SECONDS', '60')} onChange={(event) => save({ NUXIVA_REDALERT_SECONDS: event.target.value })}>
              {DURATIONS.map((seconds) => (
                <option key={seconds} value={seconds}>
                  {t('redalert_seconds', { n: seconds })}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('redalert_repeat')}>
            <select className={inputClass} disabled={busy} value={value('NUXIVA_REDALERT_REPEAT', '25')} onChange={(event) => save({ NUXIVA_REDALERT_REPEAT: event.target.value })}>
              {REPEATS.map((seconds) => (
                <option key={seconds} value={seconds}>
                  {t('redalert_seconds', { n: seconds })}
                </option>
              ))}
            </select>
          </Field>
          <div className="flex flex-col gap-3 text-xs font-semibold text-slate-700">
            <div className="flex items-center justify-between gap-3">
              <span>{t('redalert_lights')}</span>
              <Toggle checked={value('NUXIVA_REDALERT_LIGHTS', '1') !== '0'} disabled={busy} label={t('redalert_lights')} onChange={(next) => save({ NUXIVA_REDALERT_LIGHTS: next ? '1' : '0' })} />
            </div>
            <div className="flex items-center justify-between gap-3">
              <span>{t('redalert_cast')}</span>
              <Toggle checked={value('NUXIVA_REDALERT_CAST', '1') !== '0'} disabled={busy} label={t('redalert_cast')} onChange={(next) => save({ NUXIVA_REDALERT_CAST: next ? '1' : '0' })} />
            </div>
          </div>
        </div>
      </Panel>

      <Panel title={t('redalert_excluded_title')} icon={<Lightbulb className="h-4 w-4 text-yellow-300" aria-hidden="true" />}>
        <p className="mb-3 text-xs text-slate-600">{t('redalert_excluded_hint')}</p>
        {!lights.data || lights.data.lights.length === 0 ? (
          <Empty>{t('redalert_no_lights')}</Empty>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {lights.data.lights.map((light) => {
              const skipped = excluded.has(light.id);
              return (
                <li key={light.id}>
                  <button
                    type="button"
                    aria-pressed={skipped}
                    disabled={busy}
                    onClick={() => toggleLight(light.id)}
                    className={`rounded-xl border px-3 py-1.5 text-xs font-semibold transition disabled:opacity-50 ${skipped ? 'border-slate-300 bg-slate-200 text-slate-600 line-through' : 'border-rose-500/40 bg-rose-500/10 text-rose-800'}`}
                  >
                    {light.name}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </Panel>
    </div>
  );
};
