import React from 'react';
import { Cable, Loader2 } from 'lucide-react';
import { ControlScope } from '../console/data/nodeConsoleApi';
import { ModuleFrame, Notice } from '../shared/components/ModuleFrame';
import { EdgePanel } from './components/EdgePanel';
import { LinkStatusPanel } from './components/LinkStatusPanel';
import { LinksPanel } from './components/LinksPanel';
import { PairingPanel } from './components/PairingPanel';
import { RequestsPanel } from './components/RequestsPanel';
import { useLinks } from './hooks/useLinks';
import { useLinkI18n } from './scope';

interface Props {
  readonly nodeId?: string;
  readonly scope?: ControlScope;
}

export const View: React.FC<Props> = ({ nodeId = '', scope = 'mesh' }) => {
  const { t } = useLinkI18n();
  const handle = useLinks(scope !== 'mesh');
  const overview = handle.overview;
  const node = overview?.nodes.find((n) => n.id === nodeId) ?? null;

  return (
    <ModuleFrame icon={Cable} title={t('title')} subtitle={t(scope === 'local' ? 'description_local' : 'description_node')} badge={t(`scope_${scope}`)}>
      {scope === 'mesh' && <Notice tone="warn">{t('notice_unpaired')}</Notice>}
      {scope !== 'mesh' && overview === null && (
        <p className="flex items-center gap-2 text-sm text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          {t('loading')}
        </p>
      )}
      {scope === 'local' && overview && (
        <div className="grid gap-4 xl:grid-cols-2">
          <div className="flex min-w-0 flex-col gap-4">
            <PairingPanel />
            <RequestsPanel handle={handle} />
          </div>
          <LinksPanel nodes={overview.nodes} />
        </div>
      )}
      {scope === 'paired' && overview && !node && <Notice tone="warn">{t('notice_removed')}</Notice>}
      {scope === 'paired' && node && (
        <div className="grid gap-4 xl:grid-cols-2">
          <LinkStatusPanel node={node} handle={handle} />
          <EdgePanel node={node} />
        </div>
      )}
    </ModuleFrame>
  );
};

export default View;
