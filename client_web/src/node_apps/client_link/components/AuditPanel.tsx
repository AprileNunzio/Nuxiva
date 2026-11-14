import React, { useEffect, useState } from 'react';
import { ScrollText } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Panel } from '../../shared/components/ModuleFrame';
import { AuditReport, fetchAudit } from '../data/trustApi';
import { relativeTime, useLinkI18n } from '../scope';
import { useNow } from '../hooks/useLinks';

const REFRESH_MS = 15000;

export const AuditPanel: React.FC = () => {
  const { t, lang } = useLinkI18n();
  const now = useNow(10000);
  const [report, setReport] = useState<AuditReport | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const load = () =>
      fetchAudit(controller.signal)
        .then(setReport)
        .catch((cause: unknown) => {
          if (!controller.signal.aborted) {
            reportError('node_audit_unavailable', cause);
          }
        });
    void load();
    const timer = window.setInterval(() => !document.hidden && void load(), REFRESH_MS);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, []);

  return (
    <Panel title={t('audit_title')}>
      {report && (
        <p className={`mb-2 text-xs ${report.intact ? 'text-emerald-300' : 'text-rose-300'}`}>
          {report.intact ? t('audit_ok', { count: report.count }) : t('audit_broken', { index: report.brokenAt ?? 0 })}
        </p>
      )}
      {report && report.entries.length === 0 && <p className="text-sm text-slate-500">{t('audit_empty')}</p>}
      <ul className="flex max-h-72 flex-col gap-1.5 overflow-y-auto">
        {(report?.entries ?? []).map((entry) => (
          <li key={entry.seq} className="rounded-lg border border-slate-800/80 bg-slate-950/40 px-3 py-2 text-xs">
            <p className="flex items-center gap-2 text-slate-200">
              <ScrollText className="h-3.5 w-3.5 shrink-0 text-cyan-300" aria-hidden="true" />
              <span className="font-mono">{entry.action}</span>
              <span className="truncate text-slate-400">{[entry.actor, entry.node].filter(Boolean).join(' → ')}</span>
              <span className="ml-auto shrink-0 text-[10px] text-slate-500">{relativeTime(entry.ts, now, lang)}</span>
            </p>
            {entry.detail && <p className="mt-0.5 break-all font-mono text-[10px] text-slate-500">{entry.detail}</p>}
          </li>
        ))}
      </ul>
    </Panel>
  );
};
