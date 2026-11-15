import React, { useEffect, useState } from 'react';
import { AlertTriangle, Check, Copy, KeyRound, Loader2, RefreshCw, Server, ShieldCheck, HelpCircle } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { reportError } from '../../../shared/errors/errorBus';
import { requestJson } from '../../../node_apps/shared/data/http';
import { PairingCode, createPairingCode } from '../../../node_apps/client_link/data/linkApi';
import { useNow } from '../../../node_apps/client_link/hooks/useLinks';
import { WindowsDownload } from './WindowsDownload';

export const WindowsGuide: React.FC = () => {
  const { t } = useScopedI18n('core_apps/nodes');
  const [serverUrl, setServerUrl] = useState('');
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [pairingCode, setPairingCode] = useState<PairingCode | null>(null);
  const [loadingCode, setLoadingCode] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);

  const now = useNow();
  const left = pairingCode ? Math.max(0, Math.round((pairingCode.expiresAt - now) / 1000)) : 0;
  const isLive = pairingCode !== null && left > 0;

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

  const copyUrl = async () => {
    if (!serverUrl) return;
    try {
      await navigator.clipboard.writeText(serverUrl);
      setCopiedUrl(true);
      window.setTimeout(() => setCopiedUrl(false), 3000);
    } catch (cause) {
      reportError('nodes_copy_failed', cause);
    }
  };

  const generateCode = async () => {
    setLoadingCode(true);
    try {
      setPairingCode(await createPairingCode());
    } catch (cause) {
      reportError('node_pairing_code_failed', cause);
    } finally {
      setLoadingCode(false);
    }
  };

  const copyCode = async () => {
    if (!pairingCode) return;
    try {
      await navigator.clipboard.writeText(pairingCode.code);
      setCopiedCode(true);
      window.setTimeout(() => setCopiedCode(false), 3000);
    } catch (cause) {
      reportError('nodes_copy_failed', cause);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Troubleshooting Alert Banner */}
      <section
        role="region"
        aria-label={t('windows_not_appearing_alert_title')}
        className="rounded-3xl border border-warning/40 bg-warning/10 p-5 shadow-sm"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-warning/20 text-warning">
            <AlertTriangle className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="flex-1 space-y-2">
            <h4 className="text-base font-bold text-on-surface">
              {t('windows_not_appearing_alert_title')}
            </h4>
            <p className="text-xs leading-relaxed text-on-surface-variant">
              {t('windows_not_appearing_reason')}
            </p>
            <div className="space-y-1.5 pt-1 text-xs text-on-surface">
              <p className="font-semibold text-primary">{t('windows_troubleshoot_step_1')}</p>
              <p>{t('windows_troubleshoot_step_2')}</p>
              <p>{t('windows_troubleshoot_step_3')}</p>
              <p>{t('windows_troubleshoot_step_4')}</p>
            </div>
            <div className="mt-3 rounded-2xl bg-surface-container-high/60 p-3 text-xs text-on-surface-variant">
              <p className="font-semibold text-on-surface">{t('windows_troubleshoot_reset_tip')}</p>
              <p className="mt-1 text-[11px] text-on-surface-variant">{t('windows_firewall_note')}</p>
            </div>
          </div>
        </div>
      </section>

      {/* Connection Parameters & Pairing Code */}
      <div className="grid gap-4 cq-sm:grid-cols-2">
        {/* Server Address Block */}
        <div className="flex flex-col justify-between rounded-3xl bg-surface-container p-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
              <Server className="h-4 w-4 text-primary" aria-hidden="true" />
              <span>{t('windows_server_url_label')}</span>
            </div>
            <p className="text-xs text-on-surface-variant">{t('windows_server_url_hint')}</p>
            <code className="block break-all rounded-xl bg-surface-container-highest px-3 py-2 font-mono text-xs font-semibold text-primary">
              {serverUrl || window.location.origin}
            </code>
          </div>
          <button
            type="button"
            onClick={() => void copyUrl()}
            disabled={!serverUrl}
            className="md-state mt-3 inline-flex min-h-10 w-fit items-center gap-2 rounded-full bg-primary-container px-4 py-2 text-xs font-semibold text-on-primary-container"
          >
            {copiedUrl ? <Check className="h-3.5 w-3.5 text-success" aria-hidden="true" /> : <Copy className="h-3.5 w-3.5" aria-hidden="true" />}
            {t(copiedUrl ? 'windows_server_url_copied' : 'windows_server_url_copy')}
          </button>
        </div>

        {/* 6-Digit Pairing Code Block */}
        <div className="flex flex-col justify-between rounded-3xl bg-surface-container p-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
              <KeyRound className="h-4 w-4 text-primary" aria-hidden="true" />
              <span>{t('windows_pairing_code_title')}</span>
            </div>
            <p className="text-xs text-on-surface-variant">{t('windows_pairing_code_desc')}</p>

            {isLive ? (
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-3xl font-extrabold tracking-[0.25em] text-primary sm:text-4xl" aria-live="polite">
                    {pairingCode.code}
                  </span>
                  <button
                    type="button"
                    onClick={() => void copyCode()}
                    className="md-state rounded-full bg-surface-container-highest p-2 text-on-surface"
                    title={t('windows_pairing_code_copied')}
                  >
                    {copiedCode ? <Check className="h-4 w-4 text-success" aria-hidden="true" /> : <Copy className="h-4 w-4" aria-hidden="true" />}
                  </button>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-on-surface/10">
                  <div
                    className="h-full rounded-full bg-primary transition-[width] duration-1000"
                    style={{ width: `${(left / 600) * 100}%` }}
                  />
                </div>
                <p className="text-xs text-on-surface-variant">
                  {t('windows_pairing_code_expires', {
                    minutes: Math.floor(left / 60),
                    seconds: String(left % 60).padStart(2, '0'),
                  })}
                </p>
                {pairingCode.fingerprint && (
                  <p className="flex items-center gap-1.5 text-[11px] text-on-surface-variant">
                    <ShieldCheck className="h-3.5 w-3.5 text-success" aria-hidden="true" />
                    <span>{t('windows_pairing_fingerprint')}</span>
                    <span className="break-all font-mono text-on-surface">{pairingCode.fingerprint}</span>
                  </p>
                )}
              </div>
            ) : null}
          </div>

          <button
            type="button"
            onClick={() => void generateCode()}
            disabled={loadingCode}
            className="md-state mt-3 inline-flex min-h-10 w-fit items-center gap-2 rounded-full bg-primary px-4 py-2 text-xs font-semibold text-on-primary disabled:opacity-60"
          >
            {loadingCode ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            ) : isLive ? (
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            ) : (
              <KeyRound className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            {t(isLive ? 'windows_pairing_code_regenerate' : 'windows_pairing_code_generate')}
          </button>
        </div>
      </div>

      {/* Step by Step Guide */}
      <section aria-label="Istruzioni passo-passo" className="rounded-3xl bg-surface-container-low p-5">
        <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
          Guida all&apos;installazione e collegamento
        </h4>
        <ol className="flex flex-col gap-3">
          <li className="flex gap-3 text-sm text-on-surface">
            <span className="md-glyph h-6 w-6 shrink-0 text-xs font-bold" aria-hidden="true">1</span>
            <div className="flex-1 space-y-2">
              <p>{t('windows_step_1_full')}</p>
              <WindowsDownload />
            </div>
          </li>
          <li className="flex gap-3 text-sm text-on-surface">
            <span className="md-glyph h-6 w-6 shrink-0 text-xs font-bold" aria-hidden="true">2</span>
            <p className="flex-1">{t('windows_step_2_full')}</p>
          </li>
          <li className="flex gap-3 text-sm text-on-surface">
            <span className="md-glyph h-6 w-6 shrink-0 text-xs font-bold" aria-hidden="true">3</span>
            <p className="flex-1">{t('windows_step_3_full')}</p>
          </li>
        </ol>
      </section>
    </div>
  );
};
