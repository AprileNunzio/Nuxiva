import React from 'react';
import { Panel } from '../../shared/components/ModuleFrame';
import { LinkNode } from '../data/linkApi';
import { useNow } from '../hooks/useLinks';
import { relativeTime, useLinkI18n } from '../scope';

export const LinksPanel: React.FC<{ readonly nodes: readonly LinkNode[] }> = ({ nodes }) => {
  const { t, lang } = useLinkI18n();
  const now = useNow(5000);
  const online = nodes.filter((n) => n.online).length;
  return (
    <Panel title={t('links_title', { online, total: nodes.length })}>
      {nodes.length === 0 ? (
        <p className="text-sm text-slate-500">{t('links_empty')}</p>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {nodes.map((node) => (
            <li key={node.id} className="flex items-center gap-3 rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2">
              <span
                className={`h-2.5 w-2.5 shrink-0 rounded-full ${node.online ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.7)]' : 'bg-slate-600'}`}
                aria-label={t(node.online ? 'state_online' : 'state_offline')}
              />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm text-slate-100">{node.name}</span>
                <span className="block truncate text-[11px] text-slate-500">
                  {[t(`type_${node.type}`), node.ip, node.version].filter(Boolean).join(' · ')}
                </span>
              </span>
              <span className="shrink-0 text-right text-[11px] text-slate-400">
                {node.lastSeen ? relativeTime(node.lastSeen, now, lang) : t('never_seen')}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
};
