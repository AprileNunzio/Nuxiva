import React, { useState } from 'react';
import { Loader2, Radar } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Panel } from '../../shared/components/ModuleFrame';
import { DiscoveredDevice, discoverPrinters, installPrinter } from '../data/printersApi';
import { fieldClass, usePrintersI18n } from '../scope';

const QUEUE = /^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$/;

function suggestQueue(label: string): string {
  const base = label.normalize('NFKD').replace(/[^A-Za-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 39);
  return QUEUE.test(base) ? base : 'Nuxiva_Printer';
}

export const DiscoverPanel: React.FC<{ readonly canInstall: boolean; readonly onInstalled: () => void }> = ({ canInstall, onInstalled }) => {
  const { t } = usePrintersI18n();
  const [devices, setDevices] = useState<readonly DiscoveredDevice[] | null>(null);
  const [scanning, setScanning] = useState(false);
  const [queues, setQueues] = useState<Record<string, string>>({});
  const [installing, setInstalling] = useState<string | null>(null);

  const scan = async () => {
    setScanning(true);
    try {
      setDevices(await discoverPrinters());
    } catch (cause) {
      reportError('node_printer_discover_failed', cause);
    } finally {
      setScanning(false);
    }
  };

  const install = async (device: DiscoveredDevice) => {
    const queue = queues[device.uri] ?? suggestQueue(device.label);
    setInstalling(device.uri);
    try {
      await installPrinter(device.uri, queue);
      onInstalled();
    } catch (cause) {
      reportError('node_printer_install_failed', cause);
    } finally {
      setInstalling(null);
    }
  };

  return (
    <Panel
      title={t('discover_title')}
      action={
        <button
          type="button"
          onClick={scan}
          disabled={scanning}
          className="flex items-center gap-1.5 rounded-lg border border-cyan-400/40 bg-cyan-400/10 px-2.5 py-1 text-xs font-semibold text-cyan-100 transition hover:bg-cyan-400/20 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          {scanning ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Radar className="h-3.5 w-3.5" aria-hidden="true" />}
          {t('discover_scan')}
        </button>
      }
    >
      {devices === null ? (
        <p className="text-sm text-slate-500">{t('discover_hint')}</p>
      ) : devices.length === 0 ? (
        <p className="text-sm text-slate-500">{t('discover_empty')}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {devices.map((device) => {
            const installable = canInstall && /^ipps?:\/\//.test(device.uri);
            const queue = queues[device.uri] ?? suggestQueue(device.label);
            return (
              <li key={device.uri} className="rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2">
                <p className="truncate text-sm font-semibold text-slate-100">{device.label}</p>
                <p className="truncate font-mono text-[11px] text-slate-500">{device.uri}</p>
                {installable && (
                  <div className="mt-2 flex gap-2">
                    <input
                      aria-label={t('queue_name')}
                      value={queue}
                      maxLength={40}
                      onChange={(event) => setQueues({ ...queues, [device.uri]: event.target.value })}
                      className={`${fieldClass} min-w-0 flex-1 py-1.5 font-mono text-xs`}
                    />
                    <button
                      type="button"
                      onClick={() => void install(device)}
                      disabled={!QUEUE.test(queue) || installing !== null}
                      className="flex items-center gap-1.5 rounded-lg bg-cyan-400 px-3 py-1.5 text-xs font-bold text-slate-950 transition hover:bg-cyan-300 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-100"
                    >
                      {installing === device.uri && <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />}
                      {t('install')}
                    </button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {!canInstall && <p className="mt-2 text-xs text-amber-200">{t('install_unavailable')}</p>}
    </Panel>
  );
};
