import React, { useEffect, useState } from 'react';
import { Btn, Empty, Loading, Panel, Pill, inputClass } from '../../shared/kit';
import { useResource } from '../../shared/useResource';
import * as api from '../api';
import { canArchive, canCancel, canDelete, canPause, canResume, isStatus } from '../scope';
import type { ProjectDetail } from '../types';
import { useAction } from '../useAction';
import { AgentPicker } from './AgentPicker';
import { DeleteConfirm } from './DeleteConfirm';
import { TaskList } from './TaskList';

interface Props {
  readonly id: string;
  readonly t: (key: string) => string;
  readonly onChanged: () => void;
  readonly onGone: () => void;
}

export const ProjectPanel: React.FC<Props> = ({ id, t, onChanged, onGone }) => {
  const url = api.detailUrl(id);
  const detail = useResource<ProjectDetail>(url, 5000);
  const data = detail.dataUrl === url ? detail.data : null;
  const [draft, setDraft] = useState('');
  const [confirming, setConfirming] = useState(false);
  const done = () => {
    detail.reload();
    onChanged();
  };
  const action = useAction(done);
  const project = data?.project;

  useEffect(() => {
    if (project) setDraft(project.title);
  }, [project?.title]);

  if (!data || !project) {
    return detail.error ? <Empty>{t('unreachable')}</Empty> : <Loading label={t('loading')} />;
  }

  const status = project.status;
  const saveTitle = () => void action.run(() => api.rename(id, draft), 'done_rename');
  const doDelete = async () => {
    if (await action.run(() => api.remove(id, id), 'done_delete')) onGone();
  };

  return (
    <Panel title={t('detail_title')} actions={<Pill tone="cyan">{isStatus(status) ? t(`status_${status}`) : t('status_unknown')}</Pill>}>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-2">
          <input className={`${inputClass} min-w-0 flex-1`} value={draft} maxLength={200} aria-label={t('rename_label')} onChange={(e) => setDraft(e.target.value)} />
          <Btn busy={action.busy} disabled={!draft.trim() || draft === project.title} onClick={saveTitle}>
            {t('rename')}
          </Btn>
        </div>
        <p className="text-sm text-on-surface-variant">{project.goal}</p>
        <div className="flex flex-wrap gap-2">
          {canPause(status) && (
            <Btn tone="amber" busy={action.busy} onClick={() => void action.run(() => api.control(id, 'pause'), 'done_pause')}>
              {t('pause')}
            </Btn>
          )}
          {canResume(status) && (
            <Btn tone="emerald" busy={action.busy} onClick={() => void action.run(() => api.control(id, 'resume'), 'done_resume')}>
              {t('resume')}
            </Btn>
          )}
          {canCancel(status) && (
            <Btn tone="slate" busy={action.busy} onClick={() => void action.run(() => api.control(id, 'cancel'), 'done_cancel')}>
              {t('cancel_project')}
            </Btn>
          )}
          {canArchive(status) && (
            <Btn tone="purple" busy={action.busy} onClick={() => void action.run(() => api.archive(id, !project.archived), project.archived ? 'done_unarchive' : 'done_archive')}>
              {t(project.archived ? 'unarchive' : 'archive')}
            </Btn>
          )}
          {canDelete(status) && (
            <Btn tone="rose" onClick={() => setConfirming(true)}>
              {t('delete')}
            </Btn>
          )}
        </div>
        {confirming && <DeleteConfirm projectId={id} busy={action.busy} t={t} onConfirm={() => void doDelete()} onCancel={() => setConfirming(false)} />}
        {action.notice && (
          <p role="status" className={`text-xs ${action.notice.kind === 'error' ? 'text-error' : 'text-success'}`}>
            {t(action.notice.key)}
          </p>
        )}
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-widest text-on-surface-variant">{t('agents_title')}</h3>
          <AgentPicker key={(project.assignees ?? []).join(',')} current={project.assignees ?? []} busy={action.busy} t={t} onSave={(agents) => void action.run(() => api.assign(id, agents), 'done_assign')} />
        </section>
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-widest text-on-surface-variant">{t('tasks_title')}</h3>
          {data.tasks.length === 0 ? (
            <Empty>{t('tasks_empty')}</Empty>
          ) : (
            <TaskList tasks={data.tasks} busy={action.busy} t={t} onReview={(task, act) => void action.run(() => api.review(id, task, act), 'done_review')} />
          )}
        </section>
      </div>
    </Panel>
  );
};
