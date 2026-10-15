import React, { useEffect, useState } from 'react';
import { History } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { fetchHistory } from '../api';
import { HistoryEvent } from '../types';
import { formatDateTime, panelClass, useUpdaterI18n } from '../scope';

const LEVEL_TONE: Readonly<Record<string, string>> = {
  ERROR: 'text-rose-300',
  WARN: 'text-amber-300',
  INFO: 'text-cyan-200',
};

export const HistoryPanel: React.FC<{ readonly refreshKey: string }> = ({ refreshKey }) => {
  const { t, lang } = useUpdaterI18n();
  const [events, setEvents] = useState<readonly HistoryEvent[] | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchHistory(controller.signal)
      .then(setEvents)
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          reportError('updater_history_failed', cause);
        }
      });
    return () => controller.abort();
  }, [refreshKey]);

  return (
    <section className={panelClass} aria-labelledby="upd-history-title">
      <h2 id="upd-history-title" className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
        <History className="h-4 w-4 text-cyan-300" aria-hidden="true" />
        {t('history_title')}
      </h2>
      {!events || events.length === 0 ? (
        <p className="text-sm text-slate-500">{t('history_empty')}</p>
      ) : (
        <ol className="custom-scrollbar flex max-h-80 flex-col gap-1.5 overflow-y-auto pr-1">
          {events.map((event) => (
            <li key={`${event.ts}-${event.msg}`} className="grid grid-cols-[auto_1fr] gap-x-3 text-xs">
              <time className="font-mono text-slate-500" dateTime={event.ts}>
                {formatDateTime(event.ts, lang)}
              </time>
              <span className={`break-words ${LEVEL_TONE[event.level] ?? 'text-slate-300'}`}>{event.msg}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
};
