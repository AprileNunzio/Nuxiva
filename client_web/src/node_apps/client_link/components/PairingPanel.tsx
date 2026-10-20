import React, { useState } from 'react';
import { KeyRound, Loader2, RefreshCw, ShieldCheck } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Panel } from '../../shared/components/ModuleFrame';
import { PairingCode, createPairingCode } from '../data/linkApi';
import { useNow } from '../hooks/useLinks';
import { useLinkI18n } from '../scope';

export const PairingPanel: React.FC = () => {
  const { t } = useLinkI18n();
  const [code, setCode] = useState<PairingCode | null>(null);
  const [loading, setLoading] = useState(false);
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

  return (
    <Panel title={t('pairing_title')}>
      <p className="mb-3 text-xs text-slate-500">{t('pairing_hint')}</p>
      {live ? (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-cyan-400/40 bg-cyan-400/5 p-4">
          <p className="font-mono text-4xl font-bold tracking-[0.35em] text-cyan-100 sm:text-5xl" aria-live="polite">
            {code.code}
          </p>
          <div className="h-1 w-full overflow-hidden rounded-full bg-slate-800">
            <div className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-indigo-500 transition-[width] duration-1000" style={{ width: `${(left / 600) * 100}%` }} />
          </div>
          <p className="text-xs text-slate-400">{t('pairing_expires', { minutes: Math.floor(left / 60), seconds: String(left % 60).padStart(2, '0') })}</p>
          {code.fingerprint && (
            <p className="flex items-center gap-1.5 text-[11px] text-slate-400">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-300" aria-hidden="true" />
              {t('pairing_fingerprint')} <span className="font-mono text-slate-200">{code.fingerprint}</span>
            </p>
          )}
        </div>
      ) : (
        code && <p className="mb-2 text-xs text-amber-200">{t('pairing_expired')}</p>
      )}
      <button
        type="button"
        onClick={() => void generate()}
        disabled={loading}
        className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-4 py-2.5 text-sm font-bold text-slate-950 transition hover:brightness-110 disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200"
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
    </Panel>
  );
};
