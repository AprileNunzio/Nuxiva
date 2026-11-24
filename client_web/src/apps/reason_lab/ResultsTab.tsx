import React, { useState } from 'react';
import { Btn, Empty, Field, Loading, Panel, Pill, Stat, StatRow, Unreachable, inputClass } from '../shared/kit';
import { useResource } from '../shared/useResource';
import { downloadRun, reportUrl, rowsUrl } from './api';
import type { Row, RunReport, Slice } from './types';
import type { LabModel } from './useLab';

const PAGE = 50;
type Translate = LabModel['t'];

function Bar({ value, tone = 'bg-primary' }: { value: number; tone?: string }) {
  return (
    <div className="h-2 w-full min-w-[4rem] overflow-hidden rounded-full bg-surface-container-highest" role="img" aria-label={`${value}%`}>
      <div className={`h-full rounded-full ${tone}`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}

function Delta({ value }: { value: number }) {
  const tone = value > 0 ? 'text-success' : value < 0 ? 'text-error' : 'text-on-surface-variant';
  return <span className={`font-mono text-xs ${tone}`}>{value > 0 ? '+' : ''}{value.toFixed(2)}</span>;
}

function Breakdown({ title, rows, labelOf, other, t }: { title: string; rows: Record<string, Slice>; labelOf: (key: string) => string; other?: Record<string, Slice>; t: Translate }) {
  const entries = Object.entries(rows).sort(([a], [b]) => a.localeCompare(b));
  return (
    <Panel title={title}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[32rem] text-left text-xs">
          <thead><tr className="text-on-surface-variant">
            <th className="whitespace-nowrap py-1 pr-2">{t('group')}</th><th className="whitespace-nowrap pr-2">{t('cases')}</th><th className="whitespace-nowrap pr-2">{t('success')}</th><th className="whitespace-nowrap pr-2">{t('intent_rate')}</th><th className="whitespace-nowrap pr-2">{t('wrong_actions')}</th>{other && <th>{t('delta')}</th>}
          </tr></thead>
          <tbody>{entries.map(([key, slice]) => (
            <tr key={key} className="border-t border-outline-variant">
              <td className="py-1 pr-2 font-semibold">{labelOf(key)}</td>
              <td className="pr-2">{slice.cases}</td>
              <td className="min-w-[8rem] pr-2"><div className="flex items-center gap-2"><Bar value={slice.success_rate} /><span className="whitespace-nowrap font-mono">{slice.success_rate.toFixed(1)}%</span></div></td>
              <td className="pr-2 font-mono">{slice.intent_rate.toFixed(1)}%</td>
              <td className="pr-2 font-mono">{slice.wrong_actions}</td>
              {other && <td>{other[key] ? <Delta value={slice.success_rate - other[key].success_rate} /> : '-'}</td>}
            </tr>
          ))}</tbody>
        </table>
      </div>
    </Panel>
  );
}

function RowsTable({ id, t }: { id: string; t: Translate }) {
  const [only, setOnly] = useState('failed');
  const [lang, setLang] = useState('');
  const [offset, setOffset] = useState(0);
  const resource = useResource<{ total: number; rows: Row[] }>(rowsUrl(id, only, lang, offset, PAGE), 5000);
  const total = resource.data?.total ?? 0;
  return (
    <Panel title={t('details')}>
      <div className="mb-3 flex flex-wrap items-end gap-3">
        <Field label={t('filter')}>
          <select className={inputClass} value={only} onChange={event => { setOnly(event.target.value); setOffset(0); }}>
            {['all', 'failed', 'wrong'].map(item => <option key={item} value={item}>{t(`filter_${item}`)}</option>)}
          </select>
        </Field>
        <Field label={t('language')}><input className={`${inputClass} max-w-[6rem]`} maxLength={3} value={lang} onChange={event => { setLang(event.target.value.toLowerCase().replace(/[^a-z]/g, '')); setOffset(0); }} /></Field>
        <span className="text-xs text-on-surface-variant">{t('rows_total', { count: total })}</span>
      </div>
      {resource.error ? <Unreachable label={t('unreachable')} /> : resource.loading && !resource.data ? <Loading label={t('loading')} /> : (resource.data?.rows.length ?? 0) === 0 ? <Empty>{t('no_rows')}</Empty> : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[32rem] text-left text-xs">
            <thead><tr className="text-on-surface-variant"><th className="whitespace-nowrap py-1 pr-2">{t('case')}</th><th className="whitespace-nowrap pr-2">{t('request')}</th><th className="whitespace-nowrap pr-2">{t('expected')}</th><th className="whitespace-nowrap pr-2">{t('obtained')}</th><th className="whitespace-nowrap pr-2">{t('tokens')}</th><th>{t('latency')}</th></tr></thead>
            <tbody>{resource.data?.rows.map(row => (
              <tr key={row.case_id} className="border-t border-outline-variant align-top">
                <td className="py-1 pr-2 font-mono">{row.case_id}</td>
                <td className="max-w-[16rem] pr-2 break-words">{row.text}</td>
                <td className="pr-2">{row.expected_intent}<br /><span className="text-on-surface-variant">{row.expected_effects.join(', ')}</span></td>
                <td className="pr-2">
                  <div className="flex flex-wrap items-center gap-1">{row.completed ? row.intent : <Pill tone="rose">{t('no_answer')}</Pill>}{row.success ? <Pill tone="emerald">{t('ok')}</Pill> : <Pill tone="rose">{t('ko')}</Pill>}{row.wrong_action && <Pill tone="amber">{t('wrong_action')}</Pill>}</div>
                  <span className="text-on-surface-variant">{row.effects.join(', ')}</span>
                </td>
                <td className="pr-2 font-mono">{row.tokens}</td>
                <td className="font-mono">{row.latency_ms} ms</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      <div className="mt-3 flex gap-2">
        <Btn disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>{t('previous')}</Btn>
        <Btn disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)}>{t('next')}</Btn>
      </div>
    </Panel>
  );
}

function Compared({ id, base, t }: { id: string; base: RunReport; t: Translate }) {
  const other = useResource<RunReport>(reportUrl(id));
  const report = other.data?.report;
  if (!report || !base.report) return null;
  const labelOf = (key: string) => key;
  return (
    <>
      <Panel title={t('comparison', { a: base.run.label || base.run.model, b: other.data?.run.label || other.data?.run.model || id })}>
        <StatRow>
          <Stat label={t('success')} value={<Delta value={base.report.overall.success_rate - report.overall.success_rate} />} />
          <Stat label={t('intent_rate')} value={<Delta value={base.report.overall.intent_rate - report.overall.intent_rate} />} />
          <Stat label={t('tokens_p50')} value={<Delta value={base.report.tokens.p50 - report.tokens.p50} />} />
          <Stat label={t('latency_p50')} value={<Delta value={base.report.latency_ms.p50 - report.latency_ms.p50} />} />
        </StatRow>
      </Panel>
      <Breakdown title={t('by_language_compare')} rows={base.report.by_language} other={report.by_language} labelOf={labelOf} t={t} />
    </>
  );
}

function Report({ id, model: m }: { id: string; model: LabModel }) {
  const { t } = m;
  const resource = useResource<RunReport>(reportUrl(id), 4000);
  if (resource.error && !resource.data) return <Unreachable label={t('unreachable')} />;
  if (!resource.data) return <Loading label={t('loading')} />;
  const { run, report } = resource.data;
  const others = m.runs.filter(item => item.id !== id);
  return (
    <div className="flex flex-col gap-4">
      <Panel title={run.label || run.model}>
        <div className="mb-3 flex flex-wrap gap-2">
          <Btn onClick={() => void m.run(() => downloadRun(id, 'report'))}>{t('download_report')}</Btn>
          <Btn onClick={() => void m.run(() => downloadRun(id, 'csv'))}>{t('download_csv')}</Btn>
          <Btn onClick={() => void m.run(() => downloadRun(id, 'outcomes'))}>{t('download_outcomes')}</Btn>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-on-surface-variant">
          <Pill>{t(`state_${run.state}`)}</Pill><span>{run.model}</span><span>{run.dataset_name}</span><span>{m.time(run.started)}</span><span>{run.done}/{run.total}</span>
          {run.failed_calls > 0 && <Pill tone="amber">{t('failed_calls', { count: run.failed_calls })}</Pill>}
          {run.error && <Pill tone="rose">{t(`error_${run.error}`)}</Pill>}
        </div>
      </Panel>
      {!report ? <Empty>{t('no_results_yet')}</Empty> : (
        <>
          <StatRow>
            <Stat label={t('cases')} value={report.overall.cases} />
            <Stat label={t('success')} value={`${report.overall.success_rate.toFixed(1)}%`} tone="emerald" />
            <Stat label={t('intent_rate')} value={`${report.overall.intent_rate.toFixed(1)}%`} />
            <Stat label={t('wrong_actions')} value={report.overall.wrong_actions} tone={report.overall.wrong_actions ? 'rose' : 'emerald'} />
            <Stat label={t('language_gap')} value={`${report.language_gap_points.toFixed(1)}`} tone="amber" />
            <Stat label={t('tokens_p50')} value={Math.round(report.tokens.p50)} tone="purple" />
            <Stat label={t('latency_p50')} value={`${Math.round(report.latency_ms.p50)} ms`} tone="purple" />
            <Stat label={t('latency_p95')} value={`${Math.round(report.latency_ms.p95)} ms`} tone="purple" />
          </StatRow>
          <div className="grid gap-4 cq-xl:grid-cols-2">
            <Breakdown title={t('by_language')} rows={report.by_language} labelOf={key => key} t={t} />
            <Breakdown title={t('by_category')} rows={report.by_category} labelOf={key => t(`category_${key}`)} t={t} />
          </div>
          <Panel title={t('compare_with')}>
            <select className={inputClass} aria-label={t('compare_with')} value={m.compareRun ?? ''} onChange={event => m.setCompareRun(event.target.value || null)}>
              <option value="">{t('none')}</option>
              {others.map(item => <option key={item.id} value={item.id}>{item.label || item.model} · {m.time(item.started)}</option>)}
            </select>
          </Panel>
          {m.compareRun && others.some(item => item.id === m.compareRun) && <Compared key={m.compareRun} id={m.compareRun} base={resource.data} t={t} />}
        </>
      )}
      <RowsTable id={id} t={t} />
    </div>
  );
}

export function ResultsTab({ model: m }: { model: LabModel }) {
  const { t } = m;
  const id = m.selectedRun && m.runs.some(item => item.id === m.selectedRun) ? m.selectedRun : m.runs[0]?.id ?? null;
  if (!id) return <Empty>{t('no_runs')}</Empty>;
  return (
    <div className="flex flex-col gap-4">
      <Field label={t('run')}>
        <select className={inputClass} value={id} onChange={event => m.setSelectedRun(event.target.value)}>
          {m.runs.map(item => <option key={item.id} value={item.id}>{item.label || item.model} · {item.dataset_name} · {m.time(item.started)}</option>)}
        </select>
      </Field>
      <Report key={id} id={id} model={m} />
    </div>
  );
}
