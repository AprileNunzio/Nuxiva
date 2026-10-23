import React, { useCallback, useEffect, useState } from 'react';
import { Copy, HeartPulse, KeyRound, Trash2 } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { NewVitalDevice, VitalKind, VitalsState, addVitalDevice, fetchVitals, removeVitalDevice, rotateVitalDevice } from '../data/connectorsApi';
import { chipClass, fieldClass, usePeopleI18n } from '../scope';

interface Props {
  readonly slug: string;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
}

const cardClass = 'flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4';
const REFRESH_MS = 5000;
const MAC = /^[0-9A-Fa-f]{2}([:-][0-9A-Fa-f]{2}){5}$/;

export const VitalsCard: React.FC<Props> = ({ slug, busy, run }) => {
  const { t } = usePeopleI18n();
  const [state, setState] = useState<VitalsState | null>(null);
  const [tick, setTick] = useState(0);
  const [kind, setKind] = useState<VitalKind>('phone');
  const [label, setLabel] = useState('');
  const [address, setAddress] = useState('');
  const [secret, setSecret] = useState<NewVitalDevice | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchVitals(slug, controller.signal)
      .then(setState)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_connectors_failed', cause));
    return () => controller.abort();
  }, [slug, tick]);

  useEffect(() => {
    const timer = window.setInterval(() => setTick((v) => v + 1), REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  const act = useCallback(
    async (key: string, task: () => Promise<unknown>) => {
      const ok = await run(key, task, 'people_connectors_failed');
      setTick((v) => v + 1);
      return ok;
    },
    [run],
  );

  const link = (device: NewVitalDevice): string =>
    device.kind === 'phone' ? `nuxiva://vitals?server=${encodeURIComponent(window.location.origin)}&token=${encodeURIComponent(device.token)}` : device.token;

  const create = async () => {
    let created: NewVitalDevice | null = null;
    const ok = await act('vitals-add', async () => {
      created = await addVitalDevice(slug, { kind, label: label.trim(), address: address.trim() });
    });
    if (ok && created) {
      const fresh: NewVitalDevice = created;
      setSecret(fresh.token ? fresh : null);
      setLabel('');
      setAddress('');
    }
  };

  const rotate = async (id: string, name: string) => {
    let token = '';
    const ok = await act(`vitals-rotate:${id}`, async () => {
      token = await rotateVitalDevice(slug, id);
    });
    if (ok && token) {
      setSecret({ kind: 'push', label: name, address: '', token });
    }
  };

  if (!state) {
    return null;
  }
  const needsAddress = kind === 'ble';
  const valid = (needsAddress ? MAC.test(address.trim()) : true) && state.devices.length < 6;
  const live = state.values.length > 0;

  return (
    <section className={`${cardClass} xl:col-span-2`} aria-labelledby="connector-vitals">
      <header className="flex items-center gap-2">
        <HeartPulse className="h-4 w-4 text-rose-700" aria-hidden="true" />
        <h3 id="connector-vitals" className="font-semibold text-slate-900">
          {t('vitals_title')}
        </h3>
        <span className={`ml-auto rounded-full border px-2 py-0.5 text-xs ${live ? 'border-emerald-300 text-emerald-800' : 'border-slate-300 text-slate-600'}`}>
          {t(live ? 'vitals_live' : state.devices.length || state.cloudReady ? 'vitals_waiting' : 'connector_not_linked')}
        </span>
      </header>
      <p className="text-xs text-slate-600">{t('vitals_hint')}</p>
      {live && (
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {state.values.map((v) => (
            <div key={v.metric} className="rounded-lg border border-slate-200 bg-white px-3 py-2">
              <dt className="text-[11px] uppercase tracking-wide text-slate-600">{t(`vitals_${v.metric}`)}</dt>
              <dd className="text-lg font-semibold text-slate-900">
                {v.value} <span className="text-xs font-normal text-slate-600">{v.unit}</span>
              </dd>
              <dd className="text-[11px] text-slate-600">{t('vitals_age', { n: Math.round(v.age), source: t(`vitals_src_${v.kind}`) })}</dd>
            </div>
          ))}
        </dl>
      )}
      {state.leaseNode && <p className="text-xs text-slate-700">{t('vitals_lease', { node: state.leaseNode })}</p>}
      <p className={`text-xs ${state.cloudReady ? 'text-emerald-800' : 'text-slate-600'}`}>{t(state.cloudReady ? 'vitals_cloud_on' : 'vitals_cloud_off')}</p>
      {state.devices.map((device) => (
        <div key={device.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm">
          <span className="min-w-0 flex-1 truncate text-slate-900">
            {device.label} · {t(`vitals_kind_${device.kind}`)}
            {device.address && <span className="ml-2 font-mono text-xs text-slate-600">{device.address}</span>}
          </span>
          {device.kind !== 'ble' && (
            <button type="button" disabled={busy !== null} onClick={() => void rotate(device.id, device.label)} className={`${chipClass} border-slate-300 px-3 text-slate-800`}>
              <KeyRound className="h-4 w-4" aria-hidden="true" />
              {t('vitals_new_key')}
            </button>
          )}
          <button type="button" disabled={busy !== null} onClick={() => void act(`vitals-del:${device.id}`, () => removeVitalDevice(slug, device.id))} className={`${chipClass} border-rose-300 px-3 text-rose-800`}>
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            {t('vitals_remove')}
          </button>
        </div>
      ))}
      {secret && (
        <div className="flex flex-col gap-2 rounded-lg border border-blue-300 bg-blue-50 p-3 text-sm text-blue-900" role="status">
          <p>{t(secret.kind === 'phone' ? 'vitals_secret_phone' : 'vitals_secret_push', { name: secret.label })}</p>
          <code className="break-all rounded bg-white px-2 py-1 text-xs text-slate-900">{link(secret)}</code>
          <div className="flex gap-2">
            <button type="button" onClick={() => void navigator.clipboard.writeText(link(secret)).catch((cause: unknown) => reportError('people_connectors_failed', cause))} className={`${chipClass} border-blue-300 px-3`}>
              <Copy className="h-4 w-4" aria-hidden="true" />
              {t('vitals_copy')}
            </button>
            <button type="button" onClick={() => setSecret(null)} className={`${chipClass} border-slate-300 px-3 text-slate-800`}>
              {t('vitals_hide')}
            </button>
          </div>
        </div>
      )}
      <div className="flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-xs text-slate-700">
          {t('vitals_kind')}
          <select className={fieldClass} value={kind} onChange={(event) => setKind(event.target.value as VitalKind)}>
            <option value="phone">{t('vitals_kind_phone')}</option>
            <option value="ble">{t('vitals_kind_ble')}</option>
            <option value="push">{t('vitals_kind_push')}</option>
          </select>
        </label>
        <label className="flex min-w-40 flex-1 flex-col gap-1 text-xs text-slate-700">
          {t('vitals_label')}
          <input className={fieldClass} value={label} maxLength={40} onChange={(event) => setLabel(event.target.value)} />
        </label>
        {needsAddress && (
          <label className="flex min-w-48 flex-col gap-1 text-xs text-slate-700">
            {t('vitals_address')}
            <input className={`${fieldClass} font-mono`} value={address} maxLength={17} placeholder="AA:BB:CC:DD:EE:FF" onChange={(event) => setAddress(event.target.value)} />
          </label>
        )}
        <button type="button" disabled={busy !== null || !valid} onClick={() => void create()} className={`${chipClass} border-blue-300 bg-blue-50 px-3 py-2 text-blue-900`}>
          <HeartPulse className="h-4 w-4" aria-hidden="true" />
          {t('vitals_add')}
        </button>
      </div>
    </section>
  );
};
