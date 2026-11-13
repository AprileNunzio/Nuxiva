import React from 'react';
import { Server } from 'lucide-react';
import { Empty, List, Panel, Pill, Row, Tone } from '../../shared/kit';
import { McpServer } from '../types';
import { Translate } from './shared';

const HEALTH_TONE: Record<McpServer['health'], Tone> = {
  ready: 'emerald',
  connecting: 'amber',
  degraded: 'amber',
  disconnected: 'rose',
  quarantined: 'rose',
};

interface Props {
  readonly servers: readonly McpServer[];
  readonly t: Translate;
}

export const ServersPanel: React.FC<Props> = ({ servers, t }) => (
  <Panel title={t('servers_title')} icon={<Server className="h-4 w-4 text-primary" aria-hidden="true" />}>
    {servers.length === 0 ? (
      <Empty>{t('servers_empty')}</Empty>
    ) : (
      <List>
        {servers.map((server) => (
          <Row key={server.id} actions={<Pill tone={HEALTH_TONE[server.health]}>{t(`health_${server.health}`)}</Pill>}>
            <b className="font-mono text-xs">{server.id}</b>
            <p className="text-[11px] text-on-surface-variant">
              {t('server_tools', { n: server.tools })} · {t('server_risk', { risk: t(`risk_${server.max_risk}`) })}
              {server.last_error ? ` · ${server.last_error}` : ''}
            </p>
          </Row>
        ))}
      </List>
    )}
  </Panel>
);
