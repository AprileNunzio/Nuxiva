import React, { useCallback, useEffect, useState } from 'react';
import { Cast as CastIcon, RefreshCw, Square } from 'lucide-react';
import { castProject, listDevices, stopCast } from '../api';
import { Btn, cx } from './ui';
import type { CastDevice, Project } from '../types';

interface Props {
  readonly project: Project;
  readonly onPublish: () => Promise<void>;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

export const CastPanel: React.FC<Props> = ({ project, onPublish, t }) => {
  const [devices, setDevices] = useState<CastDevice[]>([]);
  const [chosen, setChosen] = useState<ReadonlySet<string>>(new Set());
  const [state, setState] = useState<'idle' | 'busy' | 'ok' | 'error'>('idle');
  const [scan, setScan] = useState(false);

  const refresh = useCallback(async (force: boolean) => {
    setScan(true);
    try {
      setDevices(await listDevices(force));
    } catch {
      setDevices([]);
    } finally {
      setScan(false);
    }
  }, []);

  useEffect(() => void refresh(false), [refresh]);

  const toggle = (id: string) =>
    setChosen((current) => {
      const next = new Set(current);
      if (!next.delete(id)) next.add(id);
      return next;
    });

  const send = async (everyone: boolean) => {
    setState('busy');
    try {
      await onPublish();
      await castProject(project.id, [...chosen], everyone);
      setState('ok');
    } catch {
      setState('error');
    }
  };

  return (
    <div className="flex flex-col gap-3 p-3">
      <div className="flex items-center justify-between">
        <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t('cast_devices')}</div>
        <Btn disabled={scan} onClick={() => void refresh(true)}>
          <RefreshCw size={12} className={cx(scan && 'animate-spin')} />
          {t('cast_scan')}
        </Btn>
      </div>
      <ul className="space-y-1">
        {devices.length === 0 && <li className="py-4 text-center text-xs text-slate-400">{t('cast_none')}</li>}
        {devices.map((d) => (
          <li key={d.id}>
            <label className={cx('flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-xs', chosen.has(d.id) ? 'border-violet-300 bg-violet-50' : 'border-slate-200 bg-white')}>
              <input type="checkbox" checked={chosen.has(d.id)} onChange={() => toggle(d.id)} className="accent-violet-600" />
              <span className="flex-1 truncate font-medium text-slate-800">{d.name}</span>
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] uppercase text-slate-500">{d.kind}</span>
              {d.active && <span className="h-2 w-2 rounded-full bg-emerald-500" />}
            </label>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-1.5">
        <Btn tone="accent" disabled={chosen.size === 0 || state === 'busy'} onClick={() => void send(false)}>
          <CastIcon size={13} />
          {t('cast_selected')}
        </Btn>
        <Btn tone="soft" disabled={devices.length === 0 || state === 'busy'} onClick={() => void send(true)}>
          {t('cast_everyone')}
        </Btn>
        <Btn disabled={state === 'busy'} onClick={() => void stopCast([...chosen], chosen.size === 0)}>
          <Square size={12} />
          {t('cast_stop')}
        </Btn>
      </div>
      {state !== 'idle' && <div className={cx('text-xs', state === 'error' ? 'text-rose-600' : 'text-slate-500')}>{t(`cast_${state}`)}</div>}
    </div>
  );
};
