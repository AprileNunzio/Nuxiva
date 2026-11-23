import React, { useState } from 'react';
import { Check, Copy, Globe } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { reportError } from '../../../shared/errors/errorBus';
import { useServerAddress } from './useServerAddress';

export const ServerAddressBox: React.FC<{ readonly hintKey: string }> = ({ hintKey }) => {
  const { t } = useScopedI18n('core_apps/nodes');
  const address = useServerAddress();
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(address);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 3000);
    } catch (cause) {
      reportError('nodes_copy_failed', cause);
    }
  };

  return (
    <section aria-label={t('server_address_label')} className="flex flex-col gap-3 rounded-3xl bg-surface-container p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
          <Globe className="h-4 w-4 text-primary" aria-hidden="true" />
          <span>{t('server_address_label')}</span>
        </h4>
        <button
          type="button"
          onClick={() => void copy()}
          className="md-state inline-flex min-h-9 items-center gap-1.5 rounded-full bg-primary-container px-3 py-1.5 text-xs font-semibold text-on-primary-container"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-success" aria-hidden="true" /> : <Copy className="h-3.5 w-3.5" aria-hidden="true" />}
          <span aria-live="polite">{t(copied ? 'server_address_copied' : 'server_address_copy')}</span>
        </button>
      </div>
      <code className="block overflow-x-auto break-all rounded-2xl bg-surface-container-highest p-3 font-mono text-xs text-primary">
        {address}
      </code>
      <p className="text-xs text-on-surface-variant">{t(hintKey)}</p>
    </section>
  );
};
