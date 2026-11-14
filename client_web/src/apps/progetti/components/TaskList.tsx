import React from 'react';
import { Btn, List, Pill, Row } from '../../shared/kit';
import type { ReviewAction, TaskInfo } from '../types';

interface Props {
  readonly tasks: readonly TaskInfo[];
  readonly busy: boolean;
  readonly t: (key: string) => string;
  readonly onReview: (task: string, action: ReviewAction) => void;
}

const KNOWN = new Set(['pending', 'running', 'review', 'done', 'failed', 'cancelled', 'blocked']);

export const TaskList: React.FC<Props> = ({ tasks, busy, t, onReview }) => (
  <List>
    {tasks.map((task) => (
      <Row
        key={task.id}
        actions={
          task.status === 'review' ? (
            <>
              <Btn tone="emerald" busy={busy} onClick={() => onReview(task.id, 'approve')}>
                {t('task_approve')}
              </Btn>
              <Btn tone="amber" busy={busy} onClick={() => onReview(task.id, 'rework')}>
                {t('task_rework')}
              </Btn>
            </>
          ) : task.status === 'running' ? (
            <Btn tone="rose" busy={busy} onClick={() => onReview(task.id, 'interrupt')}>
              {t('task_interrupt')}
            </Btn>
          ) : undefined
        }
      >
        <span className="block truncate font-medium">{task.title}</span>
        <span className="flex items-center gap-2 text-xs text-on-surface-variant">
          <Pill tone={task.status === 'done' ? 'emerald' : task.status === 'failed' ? 'rose' : 'slate'}>
            {KNOWN.has(task.status) ? t(`task_${task.status}`) : t('task_unknown')}
          </Pill>
          {task.role}
        </span>
      </Row>
    ))}
  </List>
);
