import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  GitCommitHorizontal,
  History,
  RotateCcw,
} from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { fetchHistory } from '../api';
import { CommitDetail, HistoryEvent, UpdateHistoryResponse, UpdateRecord } from '../types';
import { formatDateTime, panelClass, useUpdaterI18n } from '../scope';

const PAGE_SIZE = 10;

const LEVEL_TONE: Readonly<Record<string, string>> = {
  ERROR: 'text-rose-700',
  WARN: 'text-amber-700',
  INFO: 'text-cyan-800',
};

const STATUS_CONFIG: Readonly<Record<string, { tone: string; badge: string; Icon: React.ComponentType<{ className?: string }> }>> = {
  installed: {
    tone: 'text-emerald-700',
    badge: 'border-emerald-300 bg-emerald-50 text-emerald-700',
    Icon: CheckCircle2,
  },
  failed: {
    tone: 'text-rose-700',
    badge: 'border-rose-300 bg-rose-50 text-rose-700',
    Icon: AlertCircle,
  },
  rollback: {
    tone: 'text-amber-700',
    badge: 'border-amber-300 bg-amber-50 text-amber-700',
    Icon: RotateCcw,
  },
};

export const HistoryPanel: React.FC<{ readonly refreshKey: string }> = ({ refreshKey }) => {
  const { t, lang } = useUpdaterI18n();
  const [activeTab, setActiveTab] = useState<'records' | 'events'>('records');
  const [historyData, setHistoryData] = useState<UpdateHistoryResponse | null>(null);
  const [offset, setOffset] = useState<number>(0);
  const [expandedRecordIds, setExpandedRecordIds] = useState<ReadonlySet<string>>(new Set());
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    fetchHistory(offset, PAGE_SIZE, controller.signal)
      .then((data) => {
        setHistoryData(data);
        // By default expand the newest record on the first page
        if (offset === 0 && data.records.length > 0) {
          setExpandedRecordIds(new Set([data.records[0].id]));
        }
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          reportError('updater_history_failed', cause);
        }
      })
      .finally(() => {
        setLoading(false);
      });
    return () => controller.abort();
  }, [offset, refreshKey]);

  const toggleExpanded = (id: string) => {
    setExpandedRecordIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const total = historyData?.total ?? 0;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const records = historyData?.records ?? [];
  const events = historyData?.events ?? [];

  return (
    <section className={panelClass} aria-labelledby="upd-history-title">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <h2 id="upd-history-title" className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600">
          <History className="h-4 w-4 text-cyan-700" aria-hidden="true" />
          {t('history_title')}
        </h2>

        <div className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white p-0.5 text-xs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'records'}
            onClick={() => setActiveTab('records')}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-medium transition ${
              activeTab === 'records' ? 'bg-cyan-100 text-cyan-700 shadow-sm' : 'text-slate-600 hover:text-slate-800'
            }`}
          >
            <span>{t('history_tab_records')}</span>
            <span className="rounded-full bg-slate-100 px-1.5 py-0.2 text-[10px] text-slate-700">{total}</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'events'}
            onClick={() => setActiveTab('events')}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-medium transition ${
              activeTab === 'events' ? 'bg-cyan-100 text-cyan-700 shadow-sm' : 'text-slate-600 hover:text-slate-800'
            }`}
          >
            <span>{t('history_tab_events')}</span>
            <span className="rounded-full bg-slate-100 px-1.5 py-0.2 text-[10px] text-slate-700">{events.length}</span>
          </button>
        </div>
      </div>

      {activeTab === 'records' ? (
        <div className="flex flex-col gap-3">
          {loading && !historyData ? (
            <p className="text-sm text-slate-600">{t('loading')}</p>
          ) : records.length === 0 ? (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
              <p className="text-sm text-slate-600">{t('history_empty_records')}</p>
            </div>
          ) : (
            <ol className="flex flex-col gap-3">
              {records.map((record: UpdateRecord) => {
                const isExpanded = expandedRecordIds.has(record.id);
                const statusMeta = STATUS_CONFIG[record.status] ?? STATUS_CONFIG.installed;
                const StatusIcon = statusMeta.Icon;
                const statusLabel =
                  record.status === 'failed'
                    ? t('history_status_failed')
                    : record.status === 'rollback'
                      ? t('history_status_rollback')
                      : t('history_status_installed');

                const commitsCountText =
                  record.commit_count === 1
                    ? t('history_commits_single')
                    : record.commit_count > 1
                      ? t('history_commits_count', { count: record.commit_count })
                      : null;

                return (
                  <li
                    key={record.id}
                    className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50 transition hover:border-slate-300"
                  >
                    <div
                      className="flex flex-wrap items-center justify-between gap-3 p-3.5 cursor-pointer select-none"
                      onClick={() => toggleExpanded(record.id)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          toggleExpanded(record.id);
                        }
                      }}
                      aria-expanded={isExpanded}
                    >
                      <div className="flex flex-wrap items-center gap-2.5 min-w-0">
                        <span className={`flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-semibold ${statusMeta.badge}`}>
                          <StatusIcon className="h-3.5 w-3.5" aria-hidden="true" />
                          <span>{statusLabel}</span>
                        </span>

                        <div className="flex items-center gap-1.5 font-mono text-xs font-medium text-slate-800">
                          {record.from_short && (
                            <>
                              <span className="text-slate-600">{record.from_short}</span>
                              <ArrowRight className="h-3 w-3 text-slate-500" aria-hidden="true" />
                            </>
                          )}
                          <span className="text-cyan-700 font-bold">{record.to_short}</span>
                        </div>

                        {record.reason && (
                          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600 capitalize">
                            {record.reason}
                          </span>
                        )}

                        {commitsCountText && (
                          <span className="rounded-full border border-cyan-300 bg-cyan-950/30 px-2 py-0.5 text-[11px] font-medium text-cyan-700">
                            {commitsCountText}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <time className="text-xs text-slate-600" dateTime={record.installed_at_iso}>
                          {formatDateTime(record.installed_at, lang)}
                        </time>
                        <button
                          type="button"
                          className="rounded-lg p-1 text-slate-600 hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                          aria-label={isExpanded ? t('history_hide_commits') : t('history_view_commits')}
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleExpanded(record.id);
                          }}
                        >
                          {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        </button>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="border-t border-slate-200 bg-slate-50 p-4">
                        {record.error && (
                          <div className="mb-3 rounded-lg border border-rose-300 bg-rose-950/30 p-2.5 text-xs text-rose-700">
                            <span className="font-semibold">{t('history_error_label')}: </span>
                            <span>{record.error}</span>
                          </div>
                        )}

                        {record.commits && record.commits.length > 0 ? (
                          <ol className="flex flex-col gap-3">
                            {record.commits.map((c: CommitDetail) => {
                              const hasBody = c.body && c.body.trim() !== c.title.trim();
                              return (
                                <li key={c.sha} className="rounded-lg border border-slate-200 bg-white p-3">
                                  <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
                                    <div className="flex items-center gap-2 min-w-0">
                                      <GitCommitHorizontal className="h-4 w-4 shrink-0 text-cyan-700" aria-hidden="true" />
                                      <span className="font-mono text-xs font-bold text-cyan-600">{c.short_sha}</span>
                                      <span className="text-xs font-medium text-slate-600">· {c.author}</span>
                                    </div>
                                    {c.date_iso && (
                                      <span className="text-[11px] text-slate-500 font-mono">
                                        {formatDateTime(c.timestamp, lang)}
                                      </span>
                                    )}
                                  </div>

                                  <p className="break-words text-sm font-medium text-slate-800">{c.title}</p>

                                  {hasBody && (
                                    <div className="mt-2.5 max-h-60 overflow-y-auto rounded-md border border-slate-200 bg-white p-2.5 font-mono text-xs text-slate-700 whitespace-pre-wrap break-words custom-scrollbar">
                                      {c.body}
                                    </div>
                                  )}
                                </li>
                              );
                            })}
                          </ol>
                        ) : (
                          <p className="text-xs text-slate-500">{t('history_commits_none')}</p>
                        )}
                      </div>
                    )}
                  </li>
                );
              })}
            </ol>
          )}

          {totalPages > 1 && (
            <div className="mt-2 flex items-center justify-between border-t border-slate-200 pt-3 text-xs text-slate-600">
              <span>{t('history_page_info', { current: currentPage, total: totalPages })}</span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={offset === 0}
                  onClick={() => setOffset((prev) => Math.max(0, prev - PAGE_SIZE))}
                  className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-slate-700 transition hover:bg-slate-100 disabled:opacity-40"
                >
                  {t('history_prev')}
                </button>
                <button
                  type="button"
                  disabled={offset + PAGE_SIZE >= total}
                  onClick={() => setOffset((prev) => prev + PAGE_SIZE)}
                  className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-slate-700 transition hover:bg-slate-100 disabled:opacity-40"
                >
                  {t('history_next')}
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div>
          {events.length === 0 ? (
            <p className="text-sm text-slate-500">{t('history_empty')}</p>
          ) : (
            <ol className="custom-scrollbar flex max-h-96 flex-col gap-1.5 overflow-y-auto pr-1">
              {events.map((event: HistoryEvent) => (
                <li key={`${event.ts}-${event.msg}`} className="grid grid-cols-[auto_1fr] gap-x-3 text-xs">
                  <time className="font-mono text-slate-500" dateTime={event.ts}>
                    {formatDateTime(event.ts, lang)}
                  </time>
                  <span className={`break-words ${LEVEL_TONE[event.level] ?? 'text-slate-700'}`}>{event.msg}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </section>
  );
};
