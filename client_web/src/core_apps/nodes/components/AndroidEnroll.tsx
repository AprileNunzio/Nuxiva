import React, { useState } from 'react';
import { Check, Copy, Download, ExternalLink, QrCode, RefreshCw, ShieldOff } from 'lucide-react';
import { Btn } from '../../shared/kit';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { reportError } from '../../../shared/errors/errorBus';
import { groupCode, groupFingerprint, RELEASES_URL, useAndroidPairing } from './useAndroidPairing';

const FACT = 'text-[10px] font-semibold uppercase tracking-widest text-on-surface-variant';

const Step: React.FC<{ readonly title: string; readonly children: React.ReactNode }> = ({ title, children }) => (
  <section className="flex min-w-0 flex-col gap-3" aria-label={title}>
    <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-on-surface-variant">{title}</h4>
    {children}
  </section>
);

export const AndroidEnroll: React.FC = () => {
  const { t } = useScopedI18n('core_apps/nodes');
  const state = useAndroidPairing();
  const { apk, pairing, phase } = state;
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    if (!pairing) return;
    try {
      await navigator.clipboard.writeText(pairing.link);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 3000);
    } catch (cause) {
      reportError('nodes_copy_failed', cause);
    }
  };

  const minutes = String(Math.floor(state.remaining / 60)).padStart(2, '0');
  const seconds = String(state.remaining % 60).padStart(2, '0');

  return (
    <div className="grid min-w-0 gap-6 cq-lg:grid-cols-2">
      <Step title={t('android_apk_title')}>
        {apk ? (
          <div className="flex flex-wrap items-start gap-4">
            {state.apkImage && <img src={state.apkImage} alt={t('android_apk_qr_alt')} width={148} height={148} className="h-36 w-36 rounded-2xl bg-white p-1" />}
            <div className="flex min-w-0 flex-1 basis-48 flex-col gap-2 text-xs text-on-surface-variant">
              <a
                className="md-state inline-flex min-h-11 w-fit items-center justify-center gap-2 rounded-full bg-primary px-4 text-sm font-semibold text-on-primary"
                href={apk.url}
                rel="noopener noreferrer"
                download={apk.name}
              >
                <Download className="h-4 w-4 shrink-0" aria-hidden="true" />
                {t('android_download_version', { version: apk.version })}
              </a>
              <p className="break-all font-mono">SHA-256 {apk.sha256}</p>
              <p>{t('android_apk_hint')}</p>
            </div>
          </div>
        ) : (
          state.loaded && (
            <p role="alert" className="flex flex-col gap-1 text-xs text-warning">
              <span>{t('android_error_android_apk_unavailable')}</span>
              <a className="inline-flex min-h-11 items-center gap-1 font-semibold underline" href={RELEASES_URL} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                {t('windows_releases_page')}
              </a>
            </p>
          )
        )}
      </Step>

      <Step title={t('android_enroll_title')}>
        <div className="flex flex-wrap items-center gap-2">
          <Btn busy={state.busy} disabled={!apk} onClick={() => void state.generate()}>
            {pairing ? <RefreshCw className="h-4 w-4 shrink-0" aria-hidden="true" /> : <QrCode className="h-4 w-4 shrink-0" aria-hidden="true" />}
            {t(pairing ? 'android_regenerate' : 'android_generate')}
          </Btn>
          {pairing && (
            <Btn tone="rose" onClick={state.revoke}>
              <ShieldOff className="h-4 w-4 shrink-0" aria-hidden="true" />
              {t('android_revoke')}
            </Btn>
          )}
        </div>
        {pairing && state.image && (
          <div className="flex flex-wrap items-start gap-4">
            <img src={state.image} alt={t('android_enroll_qr_alt')} width={200} height={200} className="h-48 w-48 rounded-2xl bg-white p-1" />
            <dl className="flex min-w-0 flex-1 basis-52 flex-col gap-3 text-xs">
              <div>
                <dt className={FACT}>{t('android_code_label')}</dt>
                <dd className="font-mono text-3xl font-bold tracking-[0.2em] text-primary" aria-label={pairing.code.split('').join(' ')}>{groupCode(pairing.code)}</dd>
              </div>
              <div>
                <dt className={FACT}>{t('android_server_label')}</dt>
                <dd className="break-all font-mono text-sm text-on-surface">{pairing.server.replace(/^https:\/\//, '')}</dd>
              </div>
              <div>
                <dt className={FACT}>{t('android_fingerprint_label')}</dt>
                <dd className="font-mono text-sm text-on-surface">{groupFingerprint(pairing.fingerprint)}</dd>
              </div>
              <div>
                <dt className={FACT}>{t('android_expires_label')}</dt>
                <dd aria-live="polite" className="font-mono text-sm font-semibold text-on-surface">{minutes}:{seconds}</dd>
              </div>
              <button type="button" onClick={() => void copy()} className="md-state inline-flex min-h-11 w-fit items-center gap-2 rounded-full bg-surface-container-high px-4 font-semibold text-on-surface">
                {copied ? <Check className="h-4 w-4" aria-hidden="true" /> : <Copy className="h-4 w-4" aria-hidden="true" />}
                {copied ? t('android_copied') : t('android_copy_link')}
              </button>
            </dl>
          </div>
        )}
        {pairing && <p className="text-xs text-on-surface-variant">{t('android_enroll_hint')}</p>}
        {pairing && phase === 'code_used' && <p role="status" className="text-xs font-semibold text-primary">{t('android_state_code_used')}</p>}
        {!pairing && phase !== 'idle' && (
          <p role="status" className={`text-xs font-semibold ${phase === 'enrolled' ? 'text-success' : 'text-on-surface-variant'}`}>
            {t(`android_state_${phase}`)}
          </p>
        )}
        {state.error && <p role="alert" className="text-xs text-error">{t(`android_error_${state.error}`)}</p>}
      </Step>
    </div>
  );
};
