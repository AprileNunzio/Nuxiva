import React from 'react';
import { MessagesSquare } from 'lucide-react';
import { Agent, BoardMessage } from '../data/teamApi';
import { panelClass, useAgentsI18n } from '../scope';

export const ActivityFeed: React.FC<{ readonly messages: readonly BoardMessage[]; readonly agents: readonly Agent[] }> = ({ messages, agents }) => {
  const { t, lang } = useAgentsI18n();
  const names = new Map(agents.map((a) => [a.id, a.name]));
  const label = (id: string) => (id === 'tutti' ? t('everyone') : id === 'console' ? t('console') : names.get(id) ?? id);
  const time = new Intl.DateTimeFormat(lang, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const rows = [...messages].reverse().slice(0, 25);
  return (
    <section className={panelClass} aria-labelledby="team-feed">
      <h2 id="team-feed" className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
        <MessagesSquare className="h-4 w-4 text-cyan-300" aria-hidden="true" />
        {t('feed_title')}
      </h2>
      {rows.length === 0 ? (
        <p className="text-sm text-slate-500">{t('feed_empty')}</p>
      ) : (
        <ol className="flex max-h-80 flex-col gap-1.5 overflow-y-auto pr-1" aria-live="polite">
          {rows.map((m, i) => (
            <li key={`${m.at}-${i}`} className="rounded-lg border border-slate-800/80 bg-slate-950/40 px-3 py-1.5 text-xs">
              <span className="font-mono text-[10px] text-slate-500">{m.at ? time.format(new Date(m.at * 1000)) : ''}</span>{' '}
              <span className="font-semibold text-cyan-200">{label(m.from)}</span>
              <span className="text-slate-500"> → </span>
              <span className="font-semibold text-indigo-200">{label(m.to)}</span>
              {m.kind && <span className="ml-1 rounded border border-slate-700 px-1 text-[10px] text-slate-400">{m.kind}</span>}
              <p className="mt-0.5 break-words text-slate-300">{m.text}</p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
};
