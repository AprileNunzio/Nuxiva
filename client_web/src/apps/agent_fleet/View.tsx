import React, { useCallback, useState } from 'react';
import { Plus } from 'lucide-react';
import { AppFrame, Btn, Empty, Loading, Panel, Unreachable } from '../shared/kit';
import { useResource } from '../shared/useResource';
import { AgentEditor } from './components/AgentEditor';
import { AgentRow } from './components/AgentRow';
import { BulkBar } from './components/BulkBar';
import { CreateDialog } from './components/CreateDialog';
import { FilterBar } from './components/FilterBar';
import { SummaryBar } from './components/SummaryBar';
import { useFleetList } from './hooks/useFleetList';
import { useFleetI18n } from './scope';
import { EMPTY_FILTERS, FleetFilters, FleetSummary } from './types';

export const View: React.FC = () => {
  const { t } = useFleetI18n();
  const [filters, setFilters] = useState<FleetFilters>(EMPTY_FILTERS);
  const [selected, setSelected] = useState('');
  const [creating, setCreating] = useState(false);
  const list = useFleetList(filters);
  const summary = useResource<FleetSummary>('/api/fleet/summary', 10000);

  const refresh = useCallback(() => {
    list.reload();
    summary.reload();
  }, [list, summary]);

  if (list.failed && list.items.length === 0 && !summary.data) {
    return <Unreachable label={t('unreachable')} />;
  }

  return (
    <AppFrame
      title={t('title')}
      description={t('description')}
      onReload={refresh}
      actions={
        <Btn onClick={() => setCreating(true)}>
          <Plus className="h-3.5 w-3.5" aria-hidden="true" />
          {t('new_agent')}
        </Btn>
      }
    >
      <SummaryBar summary={summary.data} />
      <FilterBar filters={filters} onChange={setFilters} />
      <BulkBar filters={filters} onDone={refresh} />
      <div className={`grid gap-4 ${selected ? 'lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]' : ''}`}>
        <Panel title={t('list_title')}>
          {list.loading && list.items.length === 0 ? (
            <Loading label={t('loading')} />
          ) : list.items.length === 0 ? (
            <Empty>{t('empty')}</Empty>
          ) : (
            <ul className="flex flex-col gap-2">
              {list.items.map((agent) => (
                <AgentRow key={agent.id} agent={agent} selected={agent.id === selected} onSelect={setSelected} />
              ))}
            </ul>
          )}
          <div className="mt-3 flex justify-center">
            {list.more ? (
              <Btn busy={list.loading} onClick={list.loadMore}>{t('load_more')}</Btn>
            ) : list.items.length > 0 ? (
              <span className="text-xs text-slate-500">{t('end_of_list')}</span>
            ) : null}
          </div>
        </Panel>
        {selected ? <AgentEditor agentId={selected} onClose={() => setSelected('')} onChanged={refresh} /> : null}
      </div>
      {creating ? <CreateDialog onClose={() => setCreating(false)} onCreated={(id) => { setSelected(id); refresh(); }} /> : null}
    </AppFrame>
  );
};

export default View;
