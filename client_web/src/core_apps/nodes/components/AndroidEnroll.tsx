import React, { useCallback, useEffect, useState } from 'react';
import { Copy, Download, ExternalLink, QrCode } from 'lucide-react';
import QRCode from 'qrcode';
import { Btn } from '../../shared/kit';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { reportError } from '../../../shared/errors/errorBus';
import { NodeModuleError, requestJson } from '../../../node_apps/shared/data/http';

interface ApkInfo {
  readonly version: string;
  readonly name: string;
  readonly url: string;
  readonly sha256: string;
}

interface Enrollment {
  readonly link: string;
  readonly expires: number;
  readonly apk: ApkInfo;
}

const RELEASES_URL = 'https://github.com/AprileNunzio/Nuxiva/releases';
const OFFICIAL_PREFIX = `${RELEASES_URL}/download/`;
const KNOWN_ERRORS = new Set(['android_apk_unavailable', 'enroll_https_unavailable', 'enroll_ca_missing', 'enroll_too_many_tokens']);
const QR_OPTIONS = { errorCorrectionLevel: 'M', margin: 2, width: 320 } as const;

async function toImage(value: string): Promise<string> {
  return QRCode.toDataURL(value, QR_OPTIONS);
}

export const AndroidEnroll: React.FC = () => {
  const { t } = useScopedI18n('core_apps/nodes');
  const [apk, setApk] = useState<ApkInfo | null>(null);
  const [apkImage, setApkImage] = useState('');
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [enrollment, setEnrollment] = useState<Enrollment | null>(null);
  const [enrollImage, setEnrollImage] = useState('');
  const [remaining, setRemaining] = useState(0);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    requestJson<ApkInfo>('/api/android/installer-info', { signal: controller.signal })
      .then(async (result) => {
        if (!result.url.startsWith(OFFICIAL_PREFIX)) return;
        const image = await toImage(result.url);
        if (!controller.signal.aborted) {
          setApk(result);
          setApkImage(image);
        }
      })
      .catch((cause) => {
        if (!controller.signal.aborted && !(cause instanceof NodeModuleError)) reportError('nodes_android_info_failed', cause);
      })
      .finally(() => !controller.signal.aborted && setLoaded(true));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!enrollment) return undefined;
    const tick = () => {
      const left = Math.max(0, enrollment.expires - Math.floor(Date.now() / 1000));
      setRemaining(left);
      if (left === 0) {
        setEnrollment(null);
        setEnrollImage('');
      }
    };
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [enrollment]);

  const generate = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      const result = await requestJson<Enrollment>('/api/android/enrollment', { method: 'POST', body: '{}' });
      setEnrollImage(await toImage(result.link));
      setEnrollment(result);
    } catch (cause) {
      const code = cause instanceof NodeModuleError && KNOWN_ERRORS.has(cause.code) ? cause.code : 'generic';
      setError(code);
      if (code === 'generic') reportError('nodes_android_enrollment_failed', cause);
    } finally {
      setBusy(false);
    }
  }, []);

  const copy = async () => {
    if (!enrollment) return;
    try {
      await navigator.clipboard.writeText(enrollment.link);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 3000);
    } catch (cause) {
      reportError('nodes_copy_failed', cause);
    }
  };

  const minutes = String(Math.floor(remaining / 60)).padStart(2, '0');
  const seconds = String(remaining % 60).padStart(2, '0');

  return (
    <div className="min-w-0 space-y-4">
      <section className="space-y-2" aria-label={t('android_apk_title')}>
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{t('android_apk_title')}</h3>
        {apk ? (
          <div className="flex flex-wrap items-start gap-3">
            {apkImage && <img src={apkImage} alt={t('android_apk_qr_alt')} width={160} height={160} className="h-40 w-40 rounded-xl bg-white p-1" />}
            <div className="min-w-0 flex-1 space-y-2 text-xs text-slate-700 dark:text-slate-300">
              <a
                className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-cyan-700 px-4 text-sm font-semibold text-white hover:bg-cyan-800 focus-visible:outline focus-visible:outline-2"
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
          loaded && (
            <p role="alert" className="space-y-1 text-xs text-amber-700 dark:text-amber-400">
              <span className="block">{t('android_error_android_apk_unavailable')}</span>
              <a className="inline-flex min-h-11 items-center gap-1 font-semibold underline" href={RELEASES_URL} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                {t('windows_releases_page')}
              </a>
            </p>
          )
        )}
      </section>

      <section className="space-y-2" aria-label={t('android_enroll_title')}>
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{t('android_enroll_title')}</h3>
        <Btn busy={busy} disabled={!apk} onClick={() => void generate()}>
          <QrCode className="h-4 w-4 shrink-0" aria-hidden="true" />
          {t('android_generate')}
        </Btn>
        {enrollment && enrollImage && (
          <div className="flex flex-wrap items-start gap-3">
            <img src={enrollImage} alt={t('android_enroll_qr_alt')} width={200} height={200} className="h-48 w-48 rounded-xl bg-white p-1" />
            <div className="min-w-0 flex-1 space-y-2 text-xs text-slate-700 dark:text-slate-300">
              <p aria-live="polite" className="font-semibold">{t('android_expires', { time: `${minutes}:${seconds}` })}</p>
              <p>{t('android_enroll_hint')}</p>
              <button
                type="button"
                onClick={() => void copy()}
                className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 px-3 font-semibold hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 dark:border-slate-600 dark:hover:bg-slate-800"
              >
                <Copy className="h-4 w-4" aria-hidden="true" />
                {copied ? t('android_copied') : t('android_copy_link')}
              </button>
            </div>
          </div>
        )}
        {error && (
          <p role="alert" className="text-xs text-rose-600 dark:text-rose-400">
            {t(`android_error_${error}`)}
          </p>
        )}
      </section>
    </div>
  );
};
