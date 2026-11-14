import React from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Loading, Pill, Stat, StatRow, Unreachable } from '../shared/kit';
import { useAction, useResource } from '../shared/useResource';
import { approveTool } from './api';
import { AreasPanel } from './components/AreasPanel';
import { AuditPanel } from './components/AuditPanel';
import { ServersPanel } from './components/ServersPanel';
import { ToolsPanel } from './components/ToolsPanel';
import { McpAudit, McpStatus, McpTool } from './types';

export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('core_apps/mcp');
  const status = useResource<McpStatus>('/api/mcp/status', 5000);
  const tools = useResource<{ readonly tools: readonly McpTool[] }>('/api/mcp/tools', 10000);
  const audit = useResource<McpAudit>('/api/mcp/audit?limit=100', 10000);
  const everything = () => {
    status.reload();
    tools.reload();
    audit.reload();
  };
  const { busy, run } = useAction(everything);

  if (status.loading && !status.data) {
    return <Loading label={t('loading')} />;
  }
  if (!status.data) {
    return <Unreachable label={t(status.error ? 'unreachable' : 'loading')} />;
  }

  const { metrics, servers, quarantined, areas } = status.data;
  return (
    <AppFrame title={t('title')} description={t('description')} onReload={everything}>
      <StatRow>
        <Stat label={t('stat_servers')} value={`${metrics.healthy}/${metrics.servers}`} tone={metrics.healthy === metrics.servers ? 'emerald' : 'amber'} />
        <Stat label={t('stat_tools')} value={metrics.active} />
        <Stat label={t('stat_pending')} value={metrics.pending_approval} tone={metrics.pending_approval > 0 ? 'amber' : 'slate'} />
        <Stat label={t('stat_jobs')} value={metrics.running_jobs} />
      </StatRow>
      {quarantined.length > 0 ? <Pill tone="rose">{t('quarantined', { list: quarantined.join(', ') })}</Pill> : null}
      <div className="grid gap-4 cq-lg:grid-cols-2">
        <ServersPanel servers={servers} t={t} />
        <AreasPanel areas={areas} t={t} />
      </div>
      <ToolsPanel tools={tools.data?.tools ?? []} busy={busy} t={t} onApprove={(id) => void run(() => approveTool(id), 'mcp_approve_failed')} />
      <AuditPanel audit={audit.data} lang={lang} t={t} />
    </AppFrame>
  );
};

export default View;
