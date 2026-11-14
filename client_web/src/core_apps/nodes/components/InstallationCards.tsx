import React from 'react';
import { ChevronDown, Cpu, Laptop, Monitor, Terminal } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { LinksHandle } from '../../../node_apps/client_link/hooks/useLinks';
import { Btn } from '../../shared/kit';
import { UsbPort } from '../types';
import { PcLinkPanel } from './PcLinkPanel';
import { WindowsDownload } from './WindowsDownload';

const platforms = [
  { id: 'linux', icon: Terminal, steps: 3 },
  { id: 'windows', icon: Monitor, steps: 2 },
  { id: 'macos', icon: Laptop, steps: 3 },
  { id: 'esp32', icon: Cpu, steps: 3 },
] as const;

export const InstallationCards: React.FC<{
  readonly links: LinksHandle;
  readonly usbPorts: UsbPort[] | null;
  readonly detectingUsb: boolean;
  readonly detectUsb: () => void;
}> = ({ links, usbPorts, detectingUsb, detectUsb }) => {
  const { t } = useScopedI18n('core_apps/nodes');
  return (
    <section aria-label={t('install_platforms')} className="grid items-start gap-3 cq-sm:grid-cols-2">
      {platforms.map(({ id, icon: Icon, steps }) => (
        <details key={id} className="group min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <summary className="flex min-h-16 cursor-pointer list-none items-center gap-3 px-4 py-3 font-semibold hover:bg-cyan-50 focus-visible:outline focus-visible:outline-2 dark:hover:bg-slate-800 [&::-webkit-details-marker]:hidden">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-cyan-100 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-300">
              <Icon className="h-5 w-5" aria-hidden="true" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block">{t(`install_${id}_title`)}</span>
              <span className="block text-xs font-normal text-slate-600 dark:text-slate-400">
                {t(id === 'macos' ? 'install_pending' : 'install_steps_count', { count: steps })}
              </span>
            </span>
            <ChevronDown className="h-4 w-4 shrink-0 transition group-open:rotate-180" aria-hidden="true" />
          </summary>
          <div className="space-y-3 border-t border-slate-200 p-4 dark:border-slate-700">
            <p className="text-sm text-slate-700 dark:text-slate-300">{t(`install_${id}_guide`)}</p>
            <ol className="space-y-2">
                {Array.from({ length: steps }, (_, index) => (
                  <li key={index} className="flex gap-2 text-sm text-slate-700 dark:text-slate-300">
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-slate-100 text-xs font-bold dark:bg-slate-800" aria-hidden="true">
                      {index + 1}
                    </span>
                    <span>{t(`install_${id}_step_${index + 1}`)}</span>
                  </li>
                ))}
            </ol>
            {id === 'linux' && <PcLinkPanel handle={links} />}
            {id === 'windows' && <WindowsDownload />}
            {id === 'esp32' && (
              <div className="space-y-2">
                <Btn busy={detectingUsb} onClick={detectUsb}>{t('install_esp32_start')}</Btn>
                <div aria-live="polite" className="break-all text-xs text-slate-600 dark:text-slate-400">
                  {usbPorts && (usbPorts.length ? (
                    <ul className="space-y-1">
                      {usbPorts.map((port) => <li key={port.device}>{port.device} · {port.description}</li>)}
                    </ul>
                  ) : <p>{t('install_esp32_no_ports')}</p>)}
                </div>
              </div>
            )}
          </div>
        </details>
      ))}
    </section>
  );
};
