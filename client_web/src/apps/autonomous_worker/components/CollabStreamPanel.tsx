import React, { useState } from 'react';
import { MessageSquare } from 'lucide-react';
import { useAutonomousI18n } from '../scope';
import { CollabMessage, Mission } from '../types';

interface Props {
  mission: Mission;
}

const FILTER_KINDS = [
  'all',
  'thought',
  'doubt',
  'action',
  'artifact',
  'approval',
  'rework',
  'directive',
] as const;

export const CollabStreamPanel: React.FC<Props> = ({ mission }) => {
  const { t, lang } = useAutonomousI18n();
  const [filter, setFilter] = useState<string>('all');

  const timeFmt = new Intl.DateTimeFormat(lang, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  const messages: CollabMessage[] = (mission.collab_messages || []).filter((m) =>
    filter === 'all' ? true : m.kind === filter
  );

  function kindBadgeStyle(kind: string) {
    switch (kind) {
      case 'thought':
        return 'border-indigo-700/50 bg-indigo-950/60 text-indigo-300';
      case 'doubt':
        return 'border-amber-600/50 bg-amber-950/60 text-amber-300';
      case 'approval':
        return 'border-emerald-600/50 bg-emerald-950/60 text-emerald-300';
      case 'rework':
      case 'error':
        return 'border-rose-600/50 bg-rose-950/60 text-rose-300';
      case 'artifact':
        return 'border-cyan-600/50 bg-cyan-950/60 text-cyan-300';
      case 'directive':
        return 'border-fuchsia-600/50 bg-fuchsia-950/60 text-fuchsia-300';
      default:
        return 'border-slate-700 bg-slate-900 text-slate-300';
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-cyan-400" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            {t('collab_title')} ({messages.length})
          </h3>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {FILTER_KINDS.map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => setFilter(k)}
              className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold uppercase transition ${
                filter === k
                  ? 'bg-cyan-600 text-white'
                  : 'border border-slate-800 bg-slate-950/60 text-slate-400 hover:text-slate-200'
              }`}
            >
              {t(`collab_filter_${k}`)}
            </button>
          ))}
        </div>
      </div>

      <div className="flex max-h-96 flex-col gap-2.5 overflow-y-auto pr-1">
        {messages.length === 0 ? (
          <p className="py-6 text-center text-xs text-slate-500">{t('collab_empty')}</p>
        ) : (
          [...messages]
            .slice(-60)
            .reverse()
            .map((msg) => (
              <div
                key={msg.id}
                className="flex flex-col gap-1.5 rounded-xl border border-slate-800/90 bg-slate-950/70 p-3 text-xs"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-100">
                      {msg.sender_role || msg.sender_id}
                    </span>
                    <span
                      className={`rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase ${kindBadgeStyle(
                        msg.kind
                      )}`}
                    >
                      {msg.kind}
                    </span>
                    {msg.artifact_ref && (
                      <span className="rounded bg-slate-900 px-2 py-0.5 font-mono text-[10px] text-cyan-400">
                        {msg.artifact_ref}
                      </span>
                    )}
                  </div>
                  <span className="font-mono text-[10px] text-slate-500">
                    {msg.timestamp ? timeFmt.format(new Date(msg.timestamp * 1000)) : ''}
                  </span>
                </div>
                <p className="whitespace-pre-wrap leading-relaxed text-slate-200">
                  {msg.content}
                </p>
              </div>
            ))
        )}
      </div>
    </div>
  );
};
