import React, { FormEvent, useState } from 'react';
import { Network, Search } from 'lucide-react';
import { EXPLORE_MODES, ExploreMode, ExploreResult, GraphSnapshot, exploreGraph } from '../data/graphApi';
import { fieldClass, panelClass, primaryClass, useAgentsI18n } from '../scope';

const Stat: React.FC<{ readonly label: string; readonly value: string }> = ({ label, value }) => (
  <div className="min-w-0">
    <dt className="break-words text-[11px] leading-tight uppercase tracking-[0.12em] text-slate-500">{label}</dt>
    <dd className="font-mono text-lg font-semibold text-slate-900">{value}</dd>
  </div>
);

const Heading: React.FC<{ readonly children: React.ReactNode }> = ({ children }) => (
  <h3 className="mb-2 text-xs font-semibold text-slate-700">{children}</h3>
);

export const GraphPanel: React.FC<{ readonly data: GraphSnapshot }> = ({ data }) => {
  const { t, lang } = useAgentsI18n();
  const number = new Intl.NumberFormat(lang);
  const time = new Intl.DateTimeFormat(lang, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const [mode, setMode] = useState<ExploreMode>('neighbors');
  const [target, setTarget] = useState('');
  const [other, setOther] = useState('');
  const [depth, setDepth] = useState(2);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ExploreResult | null>(null);
  const { graph, plan, consultations, shadow } = data;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!target.trim() || busy) return;
    setBusy(true);
    exploreGraph(mode, target.trim(), depth, other.trim())
      .then(setResult)
      .catch(() => setResult({ ok: false, error: 'request_failed', items: [], truncated: false }))
      .finally(() => setBusy(false));
  };

  return (
    <section className={panelClass} aria-labelledby="team-graph">
      <h2 id="team-graph" className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600">
        <Network className="h-4 w-4 text-cyan-700" aria-hidden="true" />
        {t('graph_title')}
      </h2>
      <div className="grid gap-5 lg:grid-cols-2">
        <div>
          <Heading>{graph.available ? t('graph_map') : t('graph_unavailable')}</Heading>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Stat label={t('graph_files')} value={number.format(graph.files)} />
            <Stat label={t('graph_packages')} value={number.format(graph.packages)} />
            <Stat label={t('graph_symbols')} value={number.format(graph.symbols)} />
            <Stat label={t('graph_sections')} value={number.format(graph.sections)} />
            <Stat label={t('graph_edges')} value={number.format(graph.edges)} />
            <Stat label={t('graph_skipped')} value={number.format(graph.skipped)} />
          </dl>
        </div>
        <div>
          <Heading>{t('graph_plan')}</Heading>
          {plan && plan.steps.length > 0 ? (
            <ol className="flex flex-col gap-1 text-xs text-slate-800">
              {plan.steps.map((step, index) => (
                <li key={`${step.id}-${index}`} className="flex flex-wrap gap-x-2">
                  <span className="font-mono text-slate-500">{index + 1}.</span>
                  <span className="font-semibold">{step.agent}</span>
                  <span className="min-w-0 break-words">{step.intent || step.goal}</span>
                  <span className="text-slate-500">{step.outcome || t('graph_plan_pending')}</span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-xs text-slate-500">{t('graph_plan_empty')}</p>
          )}
        </div>
        <div>
          <Heading>{t('graph_explore')}</Heading>
          <form onSubmit={submit} className="flex flex-col gap-2">
            <div className="flex flex-wrap gap-2">
              <select className={fieldClass} value={mode} onChange={(e) => setMode(e.target.value as ExploreMode)} aria-label={t('graph_mode')}>
                {EXPLORE_MODES.map((m) => (
                  <option key={m} value={m}>
                    {t(`graph_mode_${m}`)}
                  </option>
                ))}
              </select>
              <input className={`${fieldClass} min-w-0 flex-1`} value={target} maxLength={200} onChange={(e) => setTarget(e.target.value)} placeholder={t('graph_target')} aria-label={t('graph_target')} />
              {mode === 'path' && (
                <input className={`${fieldClass} min-w-0 flex-1`} value={other} maxLength={200} onChange={(e) => setOther(e.target.value)} placeholder={t('graph_other')} aria-label={t('graph_other')} />
              )}
              {(mode === 'neighbors' || mode === 'impact') && (
                <input className={`${fieldClass} w-20`} type="number" min={1} max={6} value={depth} onChange={(e) => setDepth(Math.max(1, Math.min(6, Number(e.target.value) || 1)))} aria-label={t('graph_depth')} />
              )}
              <button type="submit" className={primaryClass} disabled={busy || !target.trim()}>
                <Search className="h-4 w-4" aria-hidden="true" />
                {t('graph_search')}
              </button>
            </div>
          </form>
          {result && (
            <div className="mt-2" role="status">
              {!result.ok && <p className="text-xs text-rose-700">{t('graph_error')}</p>}
              {result.ok && result.items.length === 0 && <p className="text-xs text-slate-500">{t('graph_none')}</p>}
              <ul className="flex max-h-56 flex-col gap-1 overflow-auto text-xs text-slate-800">
                {result.items.map((item, index) => (
                  <li key={`${item.path}-${item.name}-${index}`} className="flex flex-wrap gap-x-2">
                    <span className="font-mono text-slate-500">{item.depth > 0 ? `+${item.depth}` : '·'}</span>
                    <span className="font-semibold">{item.name}</span>
                    <span className="min-w-0 break-all text-slate-500">
                      {item.path}
                      {item.line > 0 ? `:${item.line}` : ''}
                    </span>
                    {item.via && <span className="text-slate-500">{item.via}</span>}
                  </li>
                ))}
              </ul>
              {result.truncated && <p className="text-[11px] text-slate-500">{t('graph_truncated')}</p>}
            </div>
          )}
        </div>
        <div>
          <Heading>{t('graph_log')}</Heading>
          {consultations.length === 0 ? (
            <p className="text-xs text-slate-500">{t('graph_log_empty')}</p>
          ) : (
            <ul className="flex max-h-56 flex-col gap-1 overflow-auto text-xs text-slate-800">
              {consultations.map((row, index) => (
                <li key={`${row.at}-${index}`} className="flex flex-wrap gap-x-2">
                  <span className="font-mono text-slate-500">{time.format(row.at)}</span>
                  <span className="font-semibold">{row.who}</span>
                  <span>{row.tool}</span>
                  <span className="min-w-0 break-all text-slate-500">{row.target}</span>
                  <span className={row.ok ? 'text-emerald-700' : 'text-rose-700'}>{row.ok ? `${row.ms} ms` : t('graph_failed')}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <div className="mt-4 border-t border-slate-200 pt-3">
        <Heading>
          {t('graph_shadow')} · {shadow.gate.ready ? t('graph_shadow_ready') : t('graph_shadow_waiting')}
        </Heading>
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
          <Stat label={t('graph_shadow_compared')} value={number.format(shadow.compared)} />
          <Stat label={t('graph_shadow_diffs')} value={number.format(shadow.mismatched)} />
          <Stat label={t('graph_shadow_errors')} value={number.format(shadow.errors)} />
          <Stat label={t('graph_shadow_days')} value={number.format(shadow.gate.observedDays)} />
          <Stat label={t('graph_shadow_clean')} value={number.format(shadow.gate.cleanDays)} />
          <Stat label={t('graph_shadow_streak')} value={number.format(shadow.gate.streak)} />
        </dl>
        {!shadow.persistent && <p className="mt-2 text-[11px] text-slate-500">{t('graph_shadow_volatile')}</p>}
      </div>
    </section>
  );
};
