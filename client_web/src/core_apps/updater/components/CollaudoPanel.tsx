import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, Loader2, Stethoscope, XCircle } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { runCollaudo } from '../api';
import { CheckStatus, CollaudoResult } from '../types';
import { buttonClass, formatDateTime, panelClass, useUpdaterI18n } from '../scope';

const ICONS: Readonly<Record<CheckStatus, { icon: typeof CheckCircle2; tone: string }>> = {
  PASS: { icon: CheckCircle2, tone: 'text-emerald-700' },
  WARN: { icon: AlertTriangle, tone: 'text-amber-700' },
  FAIL: { icon: XCircle, tone: 'text-rose-700' },
};

const KNOWN_CHECKS = new Set(['memory', 'disk', 'cpu', 'worktree', 'ci', 'service', 'rollback_point', 'mesh_engine']);

export const CollaudoPanel: React.FC = () => {
  const { t, lang } = useUpdaterI18n();
  const [result, setResult] = useState<CollaudoResult | null>(null);
  const [running, setRunning] = useState(false);

  const run = async () => {
    setRunning(true);
    try {
      setResult(await runCollaudo());
    } catch (cause) {
      reportError('updater_collaudo_failed', cause);
    } finally {
      setRunning(false);
    }
  };

  return (
    <section className={panelClass} aria-labelledby="upd-collaudo-title" aria-busy={running}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 id="upd-collaudo-title" className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600">
          <Stethoscope className="h-4 w-4 text-cyan-700" aria-hidden="true" />
          {t('collaudo_title')}
        </h2>
        <button
          type="button"
          onClick={run}
          disabled={running}
          className={`${buttonClass} border-cyan-300 bg-cyan-50 px-3 py-1.5 text-xs text-cyan-900 hover:bg-cyan-100`}
        >
          {running && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />}
          {t('collaudo_run')}
        </button>
      </div>
      {!result ? (
        <p className="text-sm text-slate-500">{t('collaudo_hint')}</p>
      ) : (
        <>
          <p className={`mb-3 text-sm font-semibold ${result.all_passed ? 'text-emerald-700' : 'text-rose-700'}`} role="status">
            {t(result.all_passed ? 'collaudo_ok' : 'collaudo_ko', { when: formatDateTime(result.timestamp, lang) ?? '' })}
          </p>
          <ul className="grid gap-2 sm:grid-cols-2">
            {result.tests.map((check) => {
              const { icon: Icon, tone } = ICONS[check.status];
              const key = KNOWN_CHECKS.has(check.id) ? check.id : 'unknown';
              return (
                <li key={check.id} className="flex items-start gap-2.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5">
                  <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${tone}`} aria-label={t(`check_status_${check.status}`)} />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-900">{t(`check_${key}`)}</p>
                    <p className="truncate font-mono text-xs text-slate-600" title={check.detail}>
                      {[check.metric, check.detail].filter(Boolean).join(' · ')}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </section>
  );
};
