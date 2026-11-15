import React, { useState } from 'react';
import { Cpu, Copy, Check, Terminal } from 'lucide-react';
import { Btn } from '../../shared/kit';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { reportError } from '../../../shared/errors/errorBus';
import { UsbPort } from '../types';

export const Esp32Guide: React.FC<{
  readonly usbPorts: UsbPort[] | null;
  readonly detectingUsb: boolean;
  readonly detectUsb: () => void;
}> = ({ usbPorts, detectingUsb, detectUsb }) => {
  const { t } = useScopedI18n('core_apps/nodes');
  const [copiedCmd, setCopiedCmd] = useState(false);

  const pioCmd = 'cd client_satellite/microcontrollers/esp32 && pio run -t upload';

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedCmd(true);
      window.setTimeout(() => setCopiedCmd(false), 3000);
    } catch (cause) {
      reportError('nodes_copy_failed', cause);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <p className="text-sm text-on-surface-variant">{t('install_esp32_guide')}</p>

      <ol className="flex flex-col gap-2">
        <li className="flex gap-3 text-sm text-on-surface">
          <span className="md-glyph h-6 w-6 shrink-0 text-xs font-bold" aria-hidden="true">1</span>
          <span className="min-w-0">{t('install_esp32_step_1')}</span>
        </li>
        <li className="flex gap-3 text-sm text-on-surface">
          <span className="md-glyph h-6 w-6 shrink-0 text-xs font-bold" aria-hidden="true">2</span>
          <span className="min-w-0">{t('install_esp32_step_2')}</span>
        </li>
        <li className="flex gap-3 text-sm text-on-surface">
          <span className="md-glyph h-6 w-6 shrink-0 text-xs font-bold" aria-hidden="true">3</span>
          <span className="min-w-0">{t('install_esp32_step_3')}</span>
        </li>
      </ol>

      <div className="grid gap-4 cq-sm:grid-cols-2">
        {/* Flashing Command */}
        <div className="rounded-3xl bg-surface-container p-4">
          <div className="flex items-center justify-between pb-2">
            <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
              <Terminal className="h-4 w-4 text-primary" aria-hidden="true" />
              <span>Flashing Firmware (PlatformIO)</span>
            </h4>
            <button
              type="button"
              onClick={() => void copy(pioCmd)}
              className="md-state inline-flex min-h-9 items-center gap-1.5 rounded-full bg-primary-container px-3 py-1.5 text-xs font-semibold text-on-primary-container"
            >
              {copiedCmd ? <Check className="h-3.5 w-3.5 text-success" aria-hidden="true" /> : <Copy className="h-3.5 w-3.5" aria-hidden="true" />}
              {copiedCmd ? 'Copiato!' : 'Copia comando'}
            </button>
          </div>
          <code className="block break-all rounded-2xl bg-surface-container-highest p-3 font-mono text-xs text-primary">
            {pioCmd}
          </code>
        </div>

        {/* USB Ports Detection */}
        <div className="rounded-3xl bg-surface-container p-4">
          <div className="flex items-center justify-between pb-2">
            <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
              <Cpu className="h-4 w-4 text-primary" aria-hidden="true" />
              <span>Porte Seriale / USB</span>
            </h4>
            <Btn busy={detectingUsb} onClick={detectUsb}>
              {t('install_esp32_start')}
            </Btn>
          </div>
          <div aria-live="polite" className="mt-2 text-xs text-on-surface-variant">
            {usbPorts ? (
              usbPorts.length ? (
                <ul className="flex flex-col gap-1.5 rounded-2xl bg-surface-container-highest p-3">
                  {usbPorts.map((port) => (
                    <li key={port.device} className="font-mono text-xs text-on-surface">
                      <span className="font-bold text-primary">{port.device}</span> · {port.description}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="rounded-2xl bg-surface-container-highest p-3">{t('install_esp32_no_ports')}</p>
              )
            ) : (
              <p className="rounded-2xl bg-surface-container-highest p-3">
                Collega la scheda ESP32 via cavo USB e premi &quot;Rileva porte USB&quot;.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
