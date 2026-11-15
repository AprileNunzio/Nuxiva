import React, { useEffect, useState } from 'react';
import { Laptop, Copy, Check, Shield, Terminal } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { reportError } from '../../../shared/errors/errorBus';
import { requestJson } from '../../../node_apps/shared/data/http';

export const MacosGuide: React.FC = () => {
  const { t } = useScopedI18n('core_apps/nodes');
  const [serverUrl, setServerUrl] = useState('');
  const [copiedCmd, setCopiedCmd] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    requestJson<{ server: string }>('/api/nodes/connection', { signal: controller.signal })
      .then((result) => setServerUrl(result.server))
      .catch(() => {
        if (typeof window !== 'undefined') {
          setServerUrl(window.location.origin);
        }
      });
    return () => controller.abort();
  }, []);

  const srv = serverUrl || (typeof window !== 'undefined' ? window.location.origin : 'http://192.168.1.100:8080');
  const macCmd = `git clone https://github.com/AprileNunzio/Nuxiva.git
cd Nuxiva/client_satellite/mac_assistant
python3 -m pip install -r requirements.txt
python3 nuxiva_satellite.py --server "${srv}"`;

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
      <div className="rounded-3xl border border-primary/20 bg-primary/5 p-4 text-xs text-on-surface-variant">
        <span className="font-semibold text-primary">{t('install_macos_dev_preview')}</span>
        <p className="mt-1">{t('install_macos_dev_guide')}</p>
      </div>

      <ol className="flex flex-col gap-2">
        <li className="flex gap-3 text-sm text-on-surface">
          <span className="md-glyph h-6 w-6 shrink-0 text-xs font-bold" aria-hidden="true">1</span>
          <span className="min-w-0">{t('install_macos_step_1')}</span>
        </li>
        <li className="flex gap-3 text-sm text-on-surface">
          <span className="md-glyph h-6 w-6 shrink-0 text-xs font-bold" aria-hidden="true">2</span>
          <span className="min-w-0">{t('install_macos_step_2')}</span>
        </li>
        <li className="flex gap-3 text-sm text-on-surface">
          <span className="md-glyph h-6 w-6 shrink-0 text-xs font-bold" aria-hidden="true">3</span>
          <span className="min-w-0">{t('install_macos_step_3')}</span>
        </li>
      </ol>

      <div className="space-y-4">
        {/* Terminal Run Box */}
        <div className="rounded-3xl bg-surface-container p-4">
          <div className="flex items-center justify-between pb-2">
            <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
              <Terminal className="h-4 w-4 text-primary" aria-hidden="true" />
              <span>Avvio da Terminale macOS</span>
            </h4>
            <button
              type="button"
              onClick={() => void copy(macCmd)}
              className="md-state inline-flex min-h-9 items-center gap-1.5 rounded-full bg-primary-container px-3 py-1.5 text-xs font-semibold text-on-primary-container"
            >
              {copiedCmd ? <Check className="h-3.5 w-3.5 text-success" aria-hidden="true" /> : <Copy className="h-3.5 w-3.5" aria-hidden="true" />}
              {copiedCmd ? 'Copiato!' : 'Copia comando'}
            </button>
          </div>
          <pre className="overflow-x-auto rounded-2xl bg-surface-container-highest p-3 font-mono text-xs text-primary">
            {macCmd}
          </pre>
        </div>

        {/* Permissions note */}
        <div className="flex items-start gap-3 rounded-2xl bg-surface-container p-4 text-xs text-on-surface-variant">
          <Shield className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
          <div>
            <p className="font-semibold text-on-surface">{t('install_macos_perm_title')}</p>
            <p className="mt-0.5">{t('install_macos_perm_desc')}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
