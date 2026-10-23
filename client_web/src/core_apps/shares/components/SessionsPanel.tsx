import React from 'react';
import { Users } from 'lucide-react';
import { Empty, List, Panel, Pill, Row } from '../../shared/kit';
import { ShareSession } from '../types';

interface SessionsPanelProps {
  readonly sessions: readonly ShareSession[];
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

export const SessionsPanel: React.FC<SessionsPanelProps> = ({ sessions, t }) => (
  <Panel title={t('sessions_title')} icon={<Users className="h-4 w-4 text-emerald-300" aria-hidden="true" />} actions={<Pill tone={sessions.length ? 'emerald' : 'slate'}>{sessions.length}</Pill>}>
    {sessions.length === 0 ? (
      <Empty>{t('sessions_empty')}</Empty>
    ) : (
      <List>
        {sessions.map((session) => (
          <Row key={`${session.pid}-${session.address}`} actions={<Pill tone="purple">{session.protocol}</Pill>}>
            <b>{session.machine}</b>
            <p className="text-xs text-slate-400">{session.user} · {session.address}</p>
            <p className="text-[11px] text-slate-500">{t('encryption')}: {session.encryption} · {t('signing')}: {session.signing}</p>
          </Row>
        ))}
      </List>
    )}
  </Panel>
);
