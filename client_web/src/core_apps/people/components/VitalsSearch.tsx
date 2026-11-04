import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Bluetooth, Loader2, Search, Smartphone } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { NearbyState, NewVitalDevice, addVitalDevice, createPhoneCode, fetchNearby, startVitalsSearch } from '../data/connectorsApi';
import { chipClass, usePeopleI18n } from '../scope';

interface Props {
  readonly slug: string;
  readonly nodes: readonly string[];
  readonly busy: string | null;
  readonly act: (key: string, task: () => Promise<unknown>) => Promise<boolean>;
  readonly onAdded: (device: NewVitalDevice) => void;
}

const POLL_MS = 2500;

const Bars: React.FC<{ readonly level: number }> = ({ level }) => (
  <span className="flex items-end gap-0.5" aria-hidden="true">
    {[1, 2, 3, 4].map((n) => (
      <i key={n} className={`w-1 rounded-sm ${n <= level ? 'bg-emerald-600' : 'bg-slate-300'}`} style={{ height: 4 + n * 3 }} />
    ))}
  </span>
);

export const VitalsSearch: React.FC<Props> = ({ slug, nodes, busy, act, onAdded }) => {
  const { t } = usePeopleI18n();
  const [near, setNear] = useState<NearbyState | null>(null);
  const [searching, setSearching] = useState(false);
  const [code, setCode] = useState<{ code: string; expiresIn: number } | null>(null);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  useEffect(() => {
    if (!searching) {
      return undefined;
    }
    const controller = new AbortController();
    const poll = () =>
      fetchNearby(slug, controller.signal)
        .then((state) => {
          if (alive.current) {
            setNear(state);
            setSearching(state.active);
          }
        })
        .catch((cause: unknown) => !controller.signal.aborted && reportError('people_connectors_failed', cause));
    void poll();
    const timer = window.setInterval(() => void poll(), POLL_MS);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [searching, slug]);

  const search = useCallback(async () => {
    const ok = await act('vitals-search', () => startVitalsSearch(slug));
    if (ok) {
      setSearching(true);
    }
  }, [act, slug]);

  const pair = async (ref: string, name: string) => {
    let created: NewVitalDevice | null = null;
    const ok = await act(`vitals-pair:${ref}`, async () => {
      created = await addVitalDevice(slug, { kind: 'ble', label: name || t('vitals_unnamed'), ref });
    });
    if (ok && created) {
      setSearching(false);
      setNear(null);
      onAdded(created);
    }
  };

  const phone = async () => {
    await act('vitals-code', async () => {
      setCode(await createPhoneCode(slug));
    });
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={busy !== null || nodes.length === 0} onClick={() => void search()} className={`${chipClass} border-blue-300 bg-blue-50 px-3 py-2 text-blue-900`}>
          {searching ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Search className="h-4 w-4" aria-hidden="true" />}
          {t(searching ? 'vitals_searching' : 'vitals_search')}
        </button>
        <button type="button" disabled={busy !== null} onClick={() => void phone()} className={`${chipClass} border-slate-300 px-3 py-2 text-slate-800`}>
          <Smartphone className="h-4 w-4" aria-hidden="true" />
          {t('vitals_phone_pair')}
        </button>
      </div>
      {nodes.length === 0 && <p className="text-xs text-amber-800">{t('vitals_no_nodes')}</p>}
      {searching && <p className="text-xs text-slate-600">{t('vitals_search_hint')}</p>}
      {near && near.found.length > 0 && (
        <ul className="flex flex-col gap-2" aria-label={t('vitals_found')}>
          {near.found.map((device) => (
            <li key={device.ref} className="flex items-center gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm">
              <Bluetooth className="h-4 w-4 text-blue-700" aria-hidden="true" />
              <span className="min-w-0 flex-1 truncate text-slate-900">
                {device.name || t('vitals_unnamed')}
                {device.standard && <span className="ml-2 rounded-full border border-emerald-300 px-2 text-[11px] text-emerald-800">{t('vitals_compatible')}</span>}
              </span>
              <Bars level={device.level} />
              <button type="button" disabled={busy !== null} onClick={() => void pair(device.ref, device.name)} className={`${chipClass} border-blue-300 px-3 text-blue-900`}>
                {t('vitals_associate')}
              </button>
            </li>
          ))}
        </ul>
      )}
      {near && !searching && near.found.length === 0 && <p className="text-xs text-slate-600">{t('vitals_none_found')}</p>}
      {code && (
        <div className="flex flex-col gap-1 rounded-lg border border-blue-300 bg-blue-50 p-3 text-sm text-blue-900" role="status">
          <p>{t('vitals_code_intro', { minutes: Math.round(code.expiresIn / 60) })}</p>
          <p className="font-mono text-2xl tracking-[0.3em] text-slate-900">{code.code}</p>
        </div>
      )}
    </div>
  );
};
