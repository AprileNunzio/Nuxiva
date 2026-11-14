import React, { useState } from 'react';
import { AppFrame, Btn, Empty, List, Loading, Panel, Pill, Row, Unreachable, inputClass } from '../shared/kit';
import { useResource } from '../shared/useResource';
import * as api from './api';
import { ProjectPanel } from './components/ProjectPanel';
import { isStatus, useProgettiI18n } from './scope';
import type { Overview } from './types';
import { useAction } from './useAction';

const GOAL_MIN = 8;
type Filter = 'active' | 'archived';

export const View: React.FC = () => {
  const { t } = useProgettiI18n();
  const list = useResource<Overview>(api.OVERVIEW_URL, 5000);
  const [selected, setSelected] = useState('');
  const [filter, setFilter] = useState<Filter>('active');
  const [goal, setGoal] = useState('');
  const create = useAction(() => window.setTimeout(list.reload, 1500));

  if (list.error && !list.data) {
    return <Unreachable label={t('unreachable')} />;
  }

  const all = list.data?.projects ?? [];
  const shown = all.filter((p) => (p.project.archived === true) === (filter === 'archived'));
  const submit = async () => {
    if (await create.run(() => api.createProject(goal.trim()), 'done_create')) setGoal('');
  };

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={list.reload}>
      <Panel title={t('new_title')}>
        <div className="flex flex-col gap-2">
          <textarea className={`${inputClass} min-h-20`} value={goal} maxLength={8000} placeholder={t('new_placeholder')} aria-label={t('new_title')} onChange={(e) => setGoal(e.target.value)} />
          <div className="flex items-center gap-3">
            <Btn busy={create.busy} disabled={goal.trim().length < GOAL_MIN} onClick={() => void submit()}>
              {t('new_submit')}
            </Btn>
            {create.notice && <span role="status" className={`text-xs ${create.notice.kind === 'error' ? 'text-error' : 'text-success'}`}>{t(create.notice.key)}</span>}
          </div>
        </div>
      </Panel>
      <div className={`grid gap-4 ${selected ? 'cq-lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]' : ''}`}>
        <Panel
          title={t('list_title')}
          actions={
            <div className="flex gap-1" role="tablist">
              {(['active', 'archived'] as const).map((value) => (
                <button key={value} type="button" role="tab" aria-selected={filter === value} onClick={() => setFilter(value)} className={`md-state rounded-full px-3 py-1 text-xs ${filter === value ? 'bg-primary text-on-primary' : 'bg-surface-container-high'}`}>
                  {t(`filter_${value}`)}
                </button>
              ))}
            </div>
          }
        >
          {list.loading && all.length === 0 ? (
            <Loading label={t('loading')} />
          ) : shown.length === 0 ? (
            <Empty>{t(filter === 'archived' ? 'empty_archived' : 'empty')}</Empty>
          ) : (
            <List>
              {shown.map(({ project, progress }) => (
                <Row key={project.id}>
                  <button type="button" aria-pressed={project.id === selected} onClick={() => setSelected(project.id === selected ? '' : project.id)} className="md-state w-full text-left">
                    <span className="block truncate font-medium">{project.title}</span>
                    <span className="flex items-center gap-2 text-xs text-on-surface-variant">
                      <Pill tone={project.status === 'running' ? 'emerald' : 'slate'}>{isStatus(project.status) ? t(`status_${project.status}`) : t('status_unknown')}</Pill>
                      {Math.min(100, progress.percent)}%
                    </span>
                  </button>
                </Row>
              ))}
            </List>
          )}
        </Panel>
        {selected && <ProjectPanel key={selected} id={selected} t={t} onChanged={list.reload} onGone={() => setSelected('')} />}
      </div>
    </AppFrame>
  );
};
