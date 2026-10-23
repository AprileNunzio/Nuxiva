import React, { FormEvent, useState } from 'react';
import { ArrowDown, ArrowUp, Check, Gavel, Pencil, Plus, Scale, Trash2, X } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, List, Loading, Panel, Pill, Row, Stat, StatRow, Unreachable, formatTime, inputClass } from '../shared/kit';
import { useAction, useResource } from '../shared/useResource';
import { addLaw, deleteLaw, reorderLaws, updateLaw } from './api';
import { LawsOverview } from './types';

export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('core_apps/laws');
  const { data, error, loading, reload } = useResource<LawsOverview>('/api/laws');
  const { busy, run } = useAction(reload);
  const [draft, setDraft] = useState('');
  const [editing, setEditing] = useState<string | null>(null);
  const [edit, setEdit] = useState('');

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (draft.trim().length < 3) {
      return;
    }
    if ((await run(() => addLaw(draft.trim()), 'laws_add_failed')) !== null) {
      setDraft('');
    }
  };

  const move = (index: number, step: number) => {
    const order = data.custom.map((law) => law.id);
    const target = index + step;
    if (target < 0 || target >= order.length) {
      return;
    }
    [order[index], order[target]] = [order[target], order[index]];
    void run(() => reorderLaws(order), 'laws_reorder_failed');
  };

  const save = async (id: string) => {
    if ((await run(() => updateLaw(id, edit.trim()), 'laws_update_failed')) !== null) {
      setEditing(null);
    }
  };

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={reload}>
      <StatRow>
        <Stat label={t('stat_fixed')} value={data.fixed.length} tone="rose" />
        <Stat label={t('stat_custom')} value={`${data.custom.length}/${data.max}`} tone="amber" />
      </StatRow>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={t('fixed_title')} icon={<Scale className="h-4 w-4 text-rose-700" aria-hidden="true" />}>
          <List>
            {data.fixed.map((law) => (
              <Row key={law.id}>
                <div className="flex items-center gap-2">
                  <Pill tone="rose">{law.n}</Pill>
                  <b>{law.title}</b>
                </div>
                <p className="mt-1 text-xs text-slate-600">{law.text}</p>
              </Row>
            ))}
          </List>
          <p className="mt-3 text-xs text-slate-500">{t('fixed_note')}</p>
        </Panel>
        <Panel title={t('custom_title')} icon={<Gavel className="h-4 w-4 text-amber-700" aria-hidden="true" />}>
          <form onSubmit={submit} className="mb-3 flex gap-2">
            <input className={inputClass} value={draft} maxLength={400} onChange={(event) => setDraft(event.target.value)} placeholder={t('add_placeholder')} aria-label={t('add_placeholder')} />
            <Btn type="submit" busy={busy} disabled={data.custom.length >= data.max}>
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
              {t('add')}
            </Btn>
          </form>
          {data.custom.length === 0 ? (
            <Empty>{t('custom_empty')}</Empty>
          ) : (
            <List>
              {data.custom.map((law, index) => (
                <Row
                  key={law.id}
                  actions={
                    editing === law.id ? (
                      <>
                        <Btn tone="emerald" busy={busy} onClick={() => void save(law.id)} title={t('save')}>
                          <Check className="h-3.5 w-3.5" aria-hidden="true" />
                        </Btn>
                        <Btn tone="slate" onClick={() => setEditing(null)} title={t('cancel')}>
                          <X className="h-3.5 w-3.5" aria-hidden="true" />
                        </Btn>
                      </>
                    ) : (
                      <>
                        <Btn tone="slate" disabled={busy || index === 0} onClick={() => move(index, -1)} title={t('move_up')}>
                          <ArrowUp className="h-3.5 w-3.5" aria-hidden="true" />
                        </Btn>
                        <Btn tone="slate" disabled={busy || index === data.custom.length - 1} onClick={() => move(index, 1)} title={t('move_down')}>
                          <ArrowDown className="h-3.5 w-3.5" aria-hidden="true" />
                        </Btn>
                        <Btn
                          tone="slate"
                          onClick={() => {
                            setEditing(law.id);
                            setEdit(law.text);
                          }}
                          title={t('edit')}
                        >
                          <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                        </Btn>
                        <Btn tone="rose" busy={busy} onClick={() => void run(() => deleteLaw(law.id), 'laws_delete_failed')} title={t('delete')}>
                          <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                        </Btn>
                      </>
                    )
                  }
                >
                  {editing === law.id ? (
                    <input className={inputClass} value={edit} maxLength={400} onChange={(event) => setEdit(event.target.value)} aria-label={t('edit')} />
                  ) : (
                    <>
                      <span>{law.text}</span>
                      <span className="mt-0.5 block text-[11px] text-slate-500">
                        {formatTime(law.created, lang)}
                        {law.origin ? ` · ${law.origin}` : ''}
                      </span>
                    </>
                  )}
                </Row>
              ))}
            </List>
          )}
        </Panel>
      </div>
    </AppFrame>
  );
};

export default View;
