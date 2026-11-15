import React from 'react';
import { AlertTriangle, CheckCircle2, CircleDashed, Loader2, RefreshCw, WifiOff } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { checkNow } from '../api';
import { useFleetOverview } from '../hooks/useFleetOverview';
import type { FleetHistoryEntry, FleetNode, FleetNodeStatus, FleetOverview, FleetSummary } from '../types';
import { buttonClass, formatDateTime, labelClass, mutedClass, panelClass, useUpdaterI18n } from '../scope';

type Translate = ReturnType<typeof useUpdaterI18n>['t'];

const SUMMARY_TONE: Readonly<Record<FleetSummary, string>> = {
  up_to_date: 'text-emerald-500',
  updating: 'text-[var(--md-sys-color-primary)]',
  outdated: 'text-amber-500',
  attention: 'text-rose-500',
};

const NODE_TONE: Readonly<Record<FleetNodeStatus, string>> = {
  up_to_date: 'text-emerald-500',
  updating: 'text-[var(--md-sys-color-primary)]',
  outdated: 'text-amber-500',
  awaiting_user: 'text-amber-500',
  failed: 'text-rose-500',
  offline: 'text-[var(--md-sys-color-on-surface-variant)]',
  unknown: 'text-[var(--md-sys-color-on-surface-variant)]',
};

const KNOWN_CODES = new Set([
  'hash_mismatch', 'selftest_failed', 'download_failed', 'boot_failed', 'integrity_mismatch',
  'invalid_signature', 'signature_invalid', 'install_blocked', 'storage_full',
]);

function SummaryIcon({ summary }: { readonly summary: FleetSummary }) {
  const className = `h-5 w-5 ${SUMMARY_TONE[summary]}`;
  if (summary === 'updating') return <Loader2 className={`${className} animate-spin`} aria-hidden="true" />;
  if (summary === 'attention') return <AlertTriangle className={className} aria-hidden="true" />;
  if (summary === 'outdated') return <CircleDashed className={className} aria-hidden="true" />;
  return <CheckCircle2 className={className} aria-hidden="true" />;
}

function describeError(code: string | null | undefined, t: Translate): string | null {
  if (!code) return null;
  return KNOWN_CODES.has(code) ? t(`fleet_error_${code}`) : code;
}

function Fact({ label, value }: { readonly label: string; readonly value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] uppercase tracking-[0.14em] text-[var(--md-sys-color-on-surface-variant)]">{label}</dt>
      <dd className="truncate text-sm font-semibold text-[var(--md-sys-color-on-surface)]">{value}</dd>
    </div>
  );
}

function HistoryList({ entries, locale, t }: { readonly entries: readonly FleetHistoryEntry[]; readonly locale: string; readonly t: Translate }) {
  if (entries.length === 0) return <p className={`mt-2 text-xs ${mutedClass}`}>{t('fleet_history_empty')}</p>;
  return (
    <ul className="mt-2 flex flex-col gap-1 text-xs">
      {entries.map((entry, index) => (
        <li key={`${entry.at ?? 0}-${index}`} className="flex flex-wrap gap-x-3">
          <span className={mutedClass}>{formatDateTime(entry.at, locale) ?? t('value_unavailable')}</span>
          <span className="font-semibold">{t(`fleet_state_${entry.state}`)}</span>
          {entry.version && <span className="font-mono">{entry.version}</span>}
          {entry.code && <span className="text-rose-500">{describeError(entry.code, t)}</span>}
        </li>
      ))}
    </ul>
  );
}

function NodeRow({ node, locale, t }: { readonly node: FleetNode; readonly locale: string; readonly t: Translate }) {
  const update = node.update;
  const error = describeError(update?.last_error?.code, t);
  return (
    <li className="py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex min-w-0 items-center gap-2 text-sm font-semibold text-[var(--md-sys-color-on-surface)]">
          {node.online ? <span className="h-2 w-2 rounded-full bg-emerald-400" aria-hidden="true" /> : <WifiOff className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" />}
          <span className="truncate">{node.name}</span>
          <span className="font-mono text-xs font-normal">{node.version ?? t('value_unavailable')}</span>
        </p>
        <span className={`text-xs font-semibold ${NODE_TONE[node.status]}`}>{t(`fleet_status_${node.status}`)}</span>
      </div>
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 cq-sm:grid-cols-3">
        <Fact label={t('fleet_last_check')} value={formatDateTime(update?.last_check ?? null, locale) ?? t('never')} />
        <Fact label={t('fleet_last_success')} value={formatDateTime(update?.last_success ?? null, locale) ?? t('never')} />
        {update?.target && <Fact label={t('fleet_target')} value={update.target} />}
      </dl>
      {error && <p className="mt-2 text-xs text-rose-500">{t('fleet_last_error', { error })}</p>}
      <details className="mt-2 text-xs">
        <summary className={`cursor-pointer ${mutedClass}`}>{t('fleet_history', { count: node.history.length })}</summary>
        <HistoryList entries={node.history} locale={locale} t={t} />
      </details>
    </li>
  );
}

function ServerBlock({ overview, locale, t }: { readonly overview: FleetOverview; readonly locale: string; readonly t: Translate }) {
  const { server } = overview;
  const error = describeError(server.last_error, t);
  return (
    <div>
      <p className={labelClass}>{t('fleet_server')}</p>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3 cq-sm:grid-cols-4">
        <Fact label={t('fleet_version')} value={server.version ?? t('value_unavailable')} />
        <Fact label={t('fleet_last_check')} value={formatDateTime(server.last_check, locale) ?? t('never')} />
        <Fact label={t('fleet_last_success')} value={formatDateTime(server.last_success, locale) ?? t('never')} />
        <Fact
          label={t('fleet_next_check')}
          value={server.auto_update ? (formatDateTime(server.next_check, locale) ?? t('fleet_auto_on')) : t('fleet_auto_off')}
        />
      </dl>
      {server.available && <p className="mt-2 text-xs text-amber-500">{t('fleet_server_available')}</p>}
      {error && <p className="mt-2 text-xs text-rose-500">{t('fleet_last_error', { error })}</p>}
    </div>
  );
}

export const FleetPanel: React.FC = () => {
  const { t, lang } = useUpdaterI18n();
  const { overview, unreachable, refresh } = useFleetOverview();
  const [checking, setChecking] = React.useState(false);

  const check = async () => {
    setChecking(true);
    try {
      await checkNow();
      refresh();
    } catch (cause) {
      reportError('updater_check_failed', cause);
    } finally {
      setChecking(false);
    }
  };

  if (!overview) {
    return <section className={panelClass} aria-busy={!unreachable}><p className={`text-sm ${mutedClass}`}>{t(unreachable ? 'status_unreachable' : 'loading')}</p></section>;
  }
  const { counts } = overview;
  return (
    <section className={`${panelClass} flex flex-col gap-5`} aria-labelledby="upd-fleet-title">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <SummaryIcon summary={overview.summary} />
          <div>
            <h2 id="upd-fleet-title" className={`text-base font-semibold ${SUMMARY_TONE[overview.summary]}`}>{t(`fleet_summary_${overview.summary}`)}</h2>
            <p className={`text-xs ${mutedClass}`}>{t('fleet_counts', { ok: counts.up_to_date, total: counts.total })}</p>
          </div>
        </div>
        <button type="button" onClick={() => void check()} disabled={checking} className={`${buttonClass} os-btn-secondary`}>
          <RefreshCw className={`h-3.5 w-3.5 ${checking ? 'animate-spin' : ''}`} aria-hidden="true" />
          <span>{t('action_check')}</span>
        </button>
      </div>
      <ServerBlock overview={overview} locale={lang} t={t} />
      <div>
        <p className={labelClass}>{t('fleet_nodes', { count: overview.nodes.length })}</p>
        {overview.nodes.length === 0 ? (
          <p className={`text-sm ${mutedClass}`}>{t('fleet_nodes_empty')}</p>
        ) : (
          <ul className="divide-y divide-[var(--md-sys-color-outline-variant)]">
            {overview.nodes.map((node) => <NodeRow key={node.id} node={node} locale={lang} t={t} />)}
          </ul>
        )}
      </div>
    </section>
  );
};
