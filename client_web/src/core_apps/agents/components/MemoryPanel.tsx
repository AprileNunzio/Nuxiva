import React from 'react';
import { Activity, Brain, TriangleAlert } from 'lucide-react';
import { Observability } from '../data/observabilityApi';
import { panelClass, useAgentsI18n } from '../scope';

const Stat: React.FC<{ readonly label: string; readonly value: string }> = ({ label, value }) => (
  <div className="min-w-0">
    <dt className="break-words text-[11px] leading-tight uppercase tracking-[0.12em] text-slate-500">{label}</dt>
    <dd className="font-mono text-lg font-semibold text-slate-900">{value}</dd>
  </div>
);

export const MemoryPanel: React.FC<{ readonly data: Observability }> = ({ data }) => {
  const { t, lang } = useAgentsI18n();
  const number = new Intl.NumberFormat(lang);
  const percent = new Intl.NumberFormat(lang, { style: 'percent', maximumFractionDigits: 1 });
  const kilobytes = new Intl.NumberFormat(lang, { maximumFractionDigits: 1 });
  const { squad, engine, memory, alerts } = data;
  return (
    <section className={panelClass} aria-labelledby="team-memory">
      <h2 id="team-memory" className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600">
        <Brain className="h-4 w-4 text-cyan-700" aria-hidden="true" />
        {t('memory_title')}
      </h2>
      {alerts.length > 0 && (
        <ul className="mb-3 flex flex-col gap-1.5" role="status">
          {alerts.map((alert) => (
            <li key={alert} className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs text-amber-900">
              <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              {t(`memory_alert_${alert}`)}
            </li>
          ))}
        </ul>
      )}
      <div className="grid gap-4 cq-sm:grid-cols-2">
        <div>
          <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-700">
            <Activity className="h-3.5 w-3.5 text-indigo-700" aria-hidden="true" />
            {t('memory_engine')} · {t(`memory_mode_${engine.mode}`)}
          </h3>
          <dl className="grid grid-cols-2 gap-3 cq-lg:grid-cols-3">
            <Stat label={t('memory_agents')} value={number.format(squad.agents)} />
            <Stat label={t('memory_workers')} value={number.format(squad.workers)} />
            <Stat label={t('memory_busy')} value={number.format(squad.busy)} />
            <Stat label={t('memory_compared')} value={number.format(engine.compared)} />
            <Stat label={t('memory_drift')} value={percent.format(engine.drift)} />
            <Stat label={t('memory_errors')} value={number.format(engine.errors)} />
          </dl>
        </div>
        <div>
          <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-700">
            <Brain className="h-3.5 w-3.5 text-indigo-700" aria-hidden="true" />
            {t('memory_hot')} · {memory.loaded ? t('memory_loaded') : t('memory_cold')}
          </h3>
          <dl className="grid grid-cols-2 gap-3 cq-lg:grid-cols-3">
            <Stat label={t('memory_people')} value={number.format(memory.persons)} />
            <Stat label={t('memory_present')} value={number.format(memory.present)} />
            <Stat label={t('memory_version')} value={number.format(memory.version)} />
            <Stat label={t('memory_size')} value={`${kilobytes.format(memory.approxBytes / 1024)} KB`} />
          </dl>
        </div>
      </div>
      <p className="mt-3 text-[11px] text-slate-500">{t('memory_privacy')}</p>
    </section>
  );
};
