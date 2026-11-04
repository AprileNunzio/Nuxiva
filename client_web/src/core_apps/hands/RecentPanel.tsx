import React from 'react';
import { Empty, List, Panel, Pill } from '../shared/kit';
import { useResource } from '../shared/useResource';
import { actionLabel, gestureLabel } from './labels';
import { RecentEvent } from './types';

type Translate = (key: string, params?: Record<string, string | number>) => string;

export const RecentPanel: React.FC<{ readonly t: Translate }> = ({ t }) => {
  const { data } = useResource<{ recent: RecentEvent[] }>('/api/hands/recent', 2000);
  const recent = [...(data?.recent ?? [])].reverse().slice(0, 12);
  return (
    <Panel title={t('recent_title')}>
      {recent.length === 0 ? <Empty>{t('recent_empty')}</Empty> : null}
      <List>
        {recent.map((event, index) => (
          <li key={index} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800">
            <span className="min-w-0 truncate">{gestureLabel(t, event.gesture)}</span>
            <span className="flex items-center gap-2">
              <Pill tone="slate">{t(`hand_${event.hand === 'unknown' ? 'any' : event.hand}`)}</Pill>
              {event.type === 'action' && event.action ? <Pill tone="emerald">{actionLabel(t, event.action)}</Pill> : null}
            </span>
          </li>
        ))}
      </List>
    </Panel>
  );
};
