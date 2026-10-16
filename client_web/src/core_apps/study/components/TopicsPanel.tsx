import React, { FormEvent, useState } from 'react';
import { BookOpen, RotateCcw, Trash2 } from 'lucide-react';
import { Btn, Empty, Field, List, Panel, Pill, Row, inputClass } from '../../shared/kit';
import { addTopic, deleteTopic, resetTopic } from '../api';
import { StudyOverview } from '../types';

interface TopicsPanelProps {
  readonly data: StudyOverview;
  readonly busy: boolean;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly run: <R>(task: () => Promise<R>, code?: string) => Promise<R | null>;
}

export const TopicsPanel: React.FC<TopicsPanelProps> = ({ data, busy, t, run }) => {
  const [name, setName] = useState('');
  const [level, setLevel] = useState(4);
  const [priority, setPriority] = useState(3);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (name.trim() && (await run(() => addTopic(name.trim(), level, priority), 'study_add_failed')) !== null) {
      setName('');
    }
  };

  return (
    <Panel title={t('topics_title')} icon={<BookOpen className="h-4 w-4 text-purple-300" aria-hidden="true" />}>
      {data.topics.length === 0 ? (
        <Empty>{t('topics_empty')}</Empty>
      ) : (
        <List>
          {data.topics.map((topic) => (
            <Row
              key={topic.id}
              actions={
                <>
                  <Btn tone="slate" busy={busy} onClick={() => void run(() => resetTopic(topic.id), 'study_reset_failed')} title={t('reset')}>
                    <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                  </Btn>
                  <Btn tone="rose" busy={busy} onClick={() => void run(() => deleteTopic(topic.id), 'study_delete_failed')} title={t('delete')}>
                    <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                  </Btn>
                </>
              }
            >
              <div className="flex flex-wrap items-center gap-2">
                <b>{topic.name}</b>
                <Pill tone="purple">{topic.level_name}</Pill>
                {topic.source === 'auto' ? <Pill tone="cyan">{t('auto')}</Pill> : null}
                {topic.due_reviews > 0 ? <Pill tone="amber">{t('reviews_due', { n: topic.due_reviews })}</Pill> : null}
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800" role="progressbar" aria-valuenow={Math.round(topic.progress * 100)} aria-valuemin={0} aria-valuemax={100}>
                <div className="h-full bg-gradient-to-r from-purple-500 to-cyan-400" style={{ width: `${Math.round(topic.progress * 100)}%` }} />
              </div>
              <p className="mt-1 text-[11px] text-slate-500">{t('topic_meta', { progress: Math.round(topic.progress * 100), cells: topic.cells, target: data.levels[String(topic.target_level)] ?? topic.target_level })}</p>
            </Row>
          ))}
        </List>
      )}
      <form onSubmit={submit} className="mt-4 grid grid-cols-2 gap-3 border-t border-slate-800 pt-4">
        <div className="col-span-2">
          <Field label={t('field_topic')}>
            <input className={inputClass} value={name} maxLength={80} onChange={(event) => setName(event.target.value)} required />
          </Field>
        </div>
        <Field label={t('field_target')}>
          <select className={inputClass} value={level} onChange={(event) => setLevel(Number(event.target.value))}>
            {Object.entries(data.levels).map(([key, label]) => (
              <option key={key} value={Number(key)}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t('field_priority')}>
          <select className={inputClass} value={priority} onChange={(event) => setPriority(Number(event.target.value))}>
            {[1, 2, 3, 4, 5].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </Field>
        <div className="col-span-2">
          <Btn type="submit" busy={busy}>
            {t('add_topic')}
          </Btn>
        </div>
      </form>
    </Panel>
  );
};
