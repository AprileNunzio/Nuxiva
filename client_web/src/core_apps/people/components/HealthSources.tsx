import React from 'react';
import { Bluetooth, Cloud, RefreshCw, Smartphone } from 'lucide-react';
import { HealthState } from '../data/healthApi';
import { chipClass, relative, usePeopleI18n } from '../scope';
import { WebcamSource } from './WebcamSource';

interface Props {
  readonly state: HealthState;
  readonly busy: string | null;
  readonly onSync: () => void;
  readonly onConnectors: () => void;
  readonly onCamera: () => void;
}

const badge = (on: boolean) => `rounded-full border px-2 py-0.5 text-xs ${on ? 'border-emerald-300 text-emerald-800' : 'border-slate-300 text-slate-600'}`;

export const HealthSources: React.FC<Props> = ({ state, busy, onSync, onConnectors, onCamera }) => {
  const { t, lang } = usePeopleI18n();
  const ble = state.devices.filter((d) => d.kind === 'ble');
  const phones = state.devices.filter((d) => d.kind !== 'ble');
  const streaming = (rows: typeof state.devices) => rows.some((d) => d.state === 'streaming' || d.state === 'connected');
  return (
    <section aria-labelledby="health-sources" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <h3 id="health-sources" className="sr-only">{t('hl_sources')}</h3>
      <article className="flex flex-col gap-2 rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50 to-white p-4">
        <header className="flex items-center gap-2">
          <Cloud className="h-4 w-4 text-blue-700" aria-hidden="true" />
          <h4 className="font-semibold text-slate-900">{t('hl_src_google')}</h4>
          <span className="ml-auto rounded-full bg-blue-600 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">{t('hl_primary')}</span>
        </header>
        <p className="text-xs text-slate-600">{t('hl_src_google_hint')}</p>
        <div className="flex flex-wrap gap-1.5">
          <span className={badge(state.cloud.health)}>{t('hl_scope_vitals')}</span>
          <span className={badge(state.cloud.activity)}>{t('hl_scope_activity')}</span>
        </div>
        {state.cloud.health && state.cloud.at > 0 && <p className="text-xs text-slate-500">{t('hl_synced', { when: relative(state.cloud.at, lang) })}</p>}
        <div className="mt-auto flex flex-wrap gap-2">
          {state.cloud.health ? (
            <button type="button" disabled={busy !== null} onClick={onSync} className={`${chipClass} border-blue-300 bg-white text-blue-900`}>
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              {t('hl_sync_now')}
            </button>
          ) : null}
          {(!state.cloud.health || !state.cloud.activity) && (
            <button type="button" onClick={onConnectors} className={`${chipClass} border-blue-300 bg-blue-600 text-white`}>
              {t(state.cloud.health ? 'hl_grant_activity' : 'hl_link_google')}
            </button>
          )}
        </div>
      </article>
      <article className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <header className="flex items-center gap-2">
          <Bluetooth className="h-4 w-4 text-indigo-700" aria-hidden="true" />
          <h4 className="font-semibold text-slate-900">{t('hl_src_ble_title')}</h4>
          <span className={`ml-auto ${badge(streaming(ble))}`}>{ble.length ? t('hl_devices', { n: ble.length }) : t('connector_not_linked')}</span>
        </header>
        <p className="text-xs text-slate-600">{t('hl_src_ble_hint')}</p>
      </article>
      <article className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <header className="flex items-center gap-2">
          <Smartphone className="h-4 w-4 text-emerald-700" aria-hidden="true" />
          <h4 className="font-semibold text-slate-900">{t('hl_src_phone')}</h4>
          <span className={`ml-auto ${badge(streaming(phones))}`}>{phones.length ? t('hl_devices', { n: phones.length }) : t('connector_not_linked')}</span>
        </header>
        <p className="text-xs text-slate-600">{t('hl_src_phone_hint')}</p>
      </article>
      <WebcamSource camera={state.camera} busy={busy} onToggle={onCamera} />
    </section>
  );
};
