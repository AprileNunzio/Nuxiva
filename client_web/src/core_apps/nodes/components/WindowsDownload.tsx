import React, { useState } from 'react';
import { Download } from 'lucide-react';
import { Btn } from '../../shared/kit';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { reportError } from '../../../shared/errors/errorBus';
import { download } from '../../../shared/http/download';

export const WindowsDownload: React.FC = () => {
  const { t } = useScopedI18n('core_apps/nodes');
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  const start = async () => {
    setBusy(true);
    setFailed(false);
    try {
      await download('/api/rpa/enrolled-client', 'NUXIVA_Assistente_Windows.zip', {
        method: 'POST',
        cache: 'no-store',
        headers: { 'X-Nuxiva-Request': '1' },
      });
    } catch (cause) {
      setFailed(true);
      reportError('nodes_windows_download_failed', cause);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-2">
      <Btn busy={busy} onClick={() => void start()}>
        <Download className="h-4 w-4 shrink-0" aria-hidden="true" />
        {t('windows_download')}
      </Btn>
      <p className="text-xs text-slate-600 dark:text-slate-400">{t('windows_download_hint')}</p>
      {failed && <p role="alert" className="text-xs text-rose-600 dark:text-rose-400">{t('windows_download_failed')}</p>}
    </div>
  );
};
