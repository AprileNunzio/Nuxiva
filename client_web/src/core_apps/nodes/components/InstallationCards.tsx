import React from 'react';
import { Cpu, Laptop, Monitor, Smartphone, Terminal } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { LinksHandle } from '../../../node_apps/client_link/hooks/useLinks';
import { Btn } from '../../shared/kit';
import { UsbPort } from '../types';
import { AndroidEnroll } from './AndroidEnroll';
import { PcLinkPanel } from './PcLinkPanel';
import { PlatformBlock } from './PlatformBlock';
import { WindowsDownload } from './WindowsDownload';

export const InstallationCards: React.FC<{
  readonly links: LinksHandle;
  readonly usbPorts: UsbPort[] | null;
  readonly detectingUsb: boolean;
  readonly detectUsb: () => void;
}> = ({ links, usbPorts, detectingUsb, detectUsb }) => {
  const { t } = useScopedI18n('core_apps/nodes');
  return (
    <section aria-label={t('install_platforms')} className="grid items-start gap-x-8 gap-y-10 cq-lg:grid-cols-2">
      <PlatformBlock id="linux" icon={Terminal} steps={3}>
        <PcLinkPanel handle={links} />
      </PlatformBlock>
      <PlatformBlock id="windows" icon={Monitor} steps={2}>
        <WindowsDownload />
      </PlatformBlock>
      <PlatformBlock id="android" icon={Smartphone} steps={4} wide>
        <AndroidEnroll />
      </PlatformBlock>
      <PlatformBlock id="esp32" icon={Cpu} steps={3}>
        <div className="flex flex-col gap-2">
          <div>
            <Btn busy={detectingUsb} onClick={detectUsb}>{t('install_esp32_start')}</Btn>
          </div>
          <div aria-live="polite" className="break-all text-xs text-on-surface-variant">
            {usbPorts &&
              (usbPorts.length ? (
                <ul className="flex flex-col gap-1">
                  {usbPorts.map((port) => <li key={port.device}>{port.device} · {port.description}</li>)}
                </ul>
              ) : (
                <p>{t('install_esp32_no_ports')}</p>
              ))}
          </div>
        </div>
      </PlatformBlock>
      <PlatformBlock id="macos" icon={Laptop} steps={3} />
    </section>
  );
};
