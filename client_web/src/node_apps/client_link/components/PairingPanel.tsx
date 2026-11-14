import React, { useState } from 'react';
import { Download, KeyRound, Loader2, RefreshCw, ShieldCheck } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Panel } from '../../shared/components/ModuleFrame';
import { PairingCode, createPairingCode, downloadSatelliteEnrollment } from '../data/linkApi';
import { useNow } from '../hooks/useLinks';
import { useLinkI18n } from '../scope';

export const PairingPanel: React.FC = () => {
  const { t } = useLinkI18n();
  const [code, setCode] = useState<PairingCode | null>(null);
  const [loading, setLoading] = useState(false);
  const [enrolling, setEnrolling] = useState(false);
  const now = useNow();
  const left = code ? Math.max(0, Math.round((code.expiresAt - now) / 1000)) : 0;
  const live = code !== null && left > 0;

  const generate = async () => {
    setLoading(true);
    try {
      setCode(await createPairingCode());
    } catch (cause) {
      reportError('node_pairing_code_failed', cause);
    } finally {
      setLoading(false);
    }
  };

  const enroll = async () => {
    setEnrolling(true);
    try {
      await downloadSatelliteEnrollment();
    } catch (cause) {
      reportError('node_satellite_enrollment_failed', cause);
    } finally {
      setEnrolling(false);
    }
  };

  return (
    <Panel flat title={t('pairing_title')}>
      <p className="mb-3 text-xs text-on-surface-variant">{t('pairing_hint')}</p>
      {live ? (
        <div className="flex flex-col items-start gap-3">
          <p className="font-mono text-4xl font-bold tracking-[0.35em] text-primary sm:text-5xl" aria-live="polite">
            {code.code}
          </p>
          <div className="h-1 w-full overflow-hidden rounded-full bg-on-surface/10">
            <div className="h-full rounded-full bg-primary transition-[width] duration-1000" style={{ width: `${(left / 600) * 100}%` }} />
          </div>
          <p className="text-xs text-on-surface-variant">{t('pairing_expires', { minutes: Math.floor(left / 60), seconds: String(left % 60).padStart(2, '0') })}</p>
          {code.fingerprint && (
            <p className="flex items-center gap-1.5 text-[11px] text-on-surface-variant">
              <ShieldCheck className="h-3.5 w-3.5 text-success" aria-hidden="true" />
              {t('pairing_fingerprint')} <span className="font-mono text-on-surface">{code.fingerprint}</span>
            </p>
          )}
        </div>
      ) : (
        code && <p className="mb-2 text-xs text-warning">{t('pairing_expired')}</p>
      )}
      <button
        type="button"
        onClick={() => void generate()}
        disabled={loading}
        className="md-state mt-3 flex min-h-11 w-full items-center justify-center gap-2 rounded-full bg-primary px-4 py-2.5 text-sm font-semibold text-on-primary disabled:opacity-60"
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : live ? (
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
        ) : (
          <KeyRound className="h-4 w-4" aria-hidden="true" />
        )}
        {t(live ? 'pairing_regenerate' : 'pairing_generate')}
      </button>
      <p className="mt-4 text-xs text-on-surface-variant">{t('satellite_enroll_hint')}</p>
      <button
        type="button"
        onClick={() => void enroll()}
        disabled={enrolling}
        className="md-state mt-2 flex min-h-11 w-full items-center justify-center gap-2 rounded-full bg-primary-container px-4 py-2.5 text-sm font-semibold text-on-primary-container disabled:opacity-60"
      >
        {enrolling ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Download className="h-4 w-4" aria-hidden="true" />}
        {t('satellite_enroll')}
      </button>
    </Panel>
  );
};
