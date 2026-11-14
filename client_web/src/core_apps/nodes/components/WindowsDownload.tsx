import React, { useEffect, useState } from 'react';
import { Download, ExternalLink } from 'lucide-react';
import { Btn } from '../../shared/kit';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { reportError } from '../../../shared/errors/errorBus';
import { download } from '../../../shared/http/download';
import { requestJson } from '../../../node_apps/shared/data/http';

interface InstallerInfo {
  readonly version: string;
  readonly name: string;
  readonly url: string;
}

const RELEASES_URL = 'https://github.com/AprileNunzio/Nuxiva/releases';
const OFFICIAL_PREFIX = `${RELEASES_URL}/download/`;

export const WindowsDownload: React.FC = () => {
  const { t } = useScopedI18n('core_apps/nodes');
  const [info, setInfo] = useState<InstallerInfo | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    requestJson<InstallerInfo>('/api/rpa/installer-info', { signal: controller.signal })
      .then((result) => result.url.startsWith(OFFICIAL_PREFIX) && setInfo(result))
      .catch(() => undefined)
      .finally(() => !controller.signal.aborted && setLoaded(true));
    return () => controller.abort();
  }, []);

  const start = async () => {
    if (!info) return;
    setBusy(true);
    setFailed(false);
    try {
      await download('/api/rpa/enrolled-installer', info.name, {
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
      <Btn busy={busy || !loaded} disabled={!info} onClick={() => void start()}>
        <Download className="h-4 w-4 shrink-0" aria-hidden="true" />
        {info ? t('windows_download_version', { version: info.version }) : t('windows_download')}
      </Btn>
      {loaded && !info && (
        <p role="alert" className="space-y-1 text-xs text-amber-700 dark:text-amber-400">
          <span className="block">{t('windows_installer_unavailable')}</span>
          <a className="inline-flex min-h-11 items-center gap-1 font-semibold underline" href={RELEASES_URL} target="_blank" rel="noopener noreferrer">
            <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
            {t('windows_releases_page')}
          </a>
        </p>
      )}
      {failed && info && (
        <p role="alert" className="space-y-1 text-xs text-rose-600 dark:text-rose-400">
          <span className="block">{t('windows_download_failed')}</span>
          <a className="inline-flex min-h-11 items-center gap-1 font-semibold underline" href={info.url} rel="noopener noreferrer" download={info.name}>
            <Download className="h-3.5 w-3.5" aria-hidden="true" />
            {t('windows_download_plain')}
          </a>
        </p>
      )}
      <p className="text-xs text-slate-600 dark:text-slate-400">{t('windows_download_hint')}</p>
    </div>
  );
};
