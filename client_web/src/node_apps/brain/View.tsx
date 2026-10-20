import React, { useCallback, useState } from 'react';
import { Brain, BrainCircuit, Cloud, HardDrive, Loader2, Workflow } from 'lucide-react';
import { ControlScope } from '../console/data/nodeConsoleApi';
import { ModuleFrame, Notice } from '../shared/components/ModuleFrame';
import { useAction, usePolled } from '../shared/hooks/useAction';
import { CloudTab } from './components/CloudTab';
import { FreeMatrixTab } from './components/FreeMatrixTab';
import { ModelsTab } from './components/ModelsTab';
import { RolesTab } from './components/RolesTab';
import { fetchBrains, fetchPool } from './data/brainApi';
import { useBrainI18n } from './scope';

interface Props {
  readonly nodeId?: string;
  readonly scope?: ControlScope;
}

const TABS = [
  ['roles', Workflow],
  ['models', HardDrive],
  ['cloud', Cloud],
  ['free_matrix', BrainCircuit],
] as const;

type Tab = (typeof TABS)[number][0];

export const View: React.FC<Props> = ({ scope = 'mesh' }) => {
  const { t } = useBrainI18n();
  const local = scope === 'local';
  const [tab, setTab] = useState<Tab>('roles');
  const overview = usePolled(fetchBrains, 'node_brain_unavailable', local, 15000);
  const pool = usePolled(fetchPool, 'node_brain_pool_unavailable', local, 30000);
  const refreshAll = useCallback(() => {
    overview.refresh();
    pool.refresh();
  }, [overview, pool]);
  const action = useAction();

  return (
    <ModuleFrame icon={Brain} title={t('title')} subtitle={t('description')} badge={t(`scope_${scope}`)}>
      {scope === 'mesh' && <Notice tone="warn">{t('notice_unpaired')}</Notice>}
      {scope === 'paired' && <Notice tone="info">{t('notice_paired')}</Notice>}
      {local && (
        <>
          <div role="tablist" aria-label={t('title')} className="flex gap-1 overflow-x-auto rounded-2xl border border-slate-800/80 bg-slate-950/60 p-1">
            {TABS.map(([id, Icon]) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={tab === id}
                onClick={() => setTab(id)}
                className={`flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                  tab === id ? 'bg-cyan-400/15 text-cyan-100' : 'text-slate-400 hover:text-white'
                }`}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {t(`tab_${id}`)}
              </button>
            ))}
          </div>
          {overview.data === null ? (
            <p className="flex items-center gap-2 text-sm text-slate-400">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              {t('loading')}
            </p>
          ) : tab === 'roles' ? (
            <RolesTab overview={overview.data} pool={pool.data ?? []} action={action} onSaved={overview.setData} />
          ) : tab === 'models' ? (
            <ModelsTab overview={overview.data} action={action} onChanged={refreshAll} />
          ) : tab === 'cloud' ? (
            <CloudTab action={action} onChanged={refreshAll} />
          ) : (
            <FreeMatrixTab action={action} onChanged={refreshAll} />
          )}
        </>
      )}
    </ModuleFrame>
  );
};

export default View;
