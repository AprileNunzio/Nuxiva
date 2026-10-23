import React, { useState } from 'react';
import { Check, Eye, Pencil, Star, Trash2 } from 'lucide-react';
import { Btn, Empty, List, Pill, Row, inputClass } from '../../shared/kit';
import { deletePlace, renamePlace, setDefault } from '../api';
import { WeatherPlace } from '../types';

type Run = <R>(task: () => Promise<R>, code?: string) => Promise<R | null>;

interface Props {
  readonly places: readonly WeatherPlace[];
  readonly defaultId: string;
  readonly selected: string;
  readonly busy: boolean;
  readonly run: Run;
  readonly onSelect: (id: string) => void;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

export const PlaceList: React.FC<Props> = ({ places, defaultId, selected, busy, run, onSelect, t }) => {
  const [editing, setEditing] = useState('');
  const [draft, setDraft] = useState('');
  const [armed, setArmed] = useState('');

  if (places.length === 0) return <Empty>{t('places_empty')}</Empty>;

  const save = async (id: string) => {
    const done = await run(() => renamePlace(id, draft).then(() => true), 'weather_failed');
    if (done) setEditing('');
  };

  const remove = async (id: string) => {
    if (armed !== id) {
      setArmed(id);
      return;
    }
    setArmed('');
    await run(() => deletePlace(id), 'weather_failed');
  };

  return (
    <List>
      {places.map((item) => (
        <Row
          key={item.id}
          actions={
            <div className="flex flex-wrap justify-end gap-1.5">
              <Btn tone={selected === item.id ? 'cyan' : 'slate'} onClick={() => onSelect(item.id)} title={t('preview')}>
                <Eye className="h-3.5 w-3.5" aria-hidden="true" />
              </Btn>
              <Btn tone="amber" busy={busy} disabled={item.id === defaultId} onClick={() => void run(() => setDefault(item.id), 'weather_failed')} title={t('make_default')}>
                <Star className="h-3.5 w-3.5" aria-hidden="true" />
              </Btn>
              <Btn
                tone="slate"
                onClick={() => {
                  setEditing(item.id);
                  setDraft(item.name);
                }}
                title={t('rename')}
              >
                <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
              </Btn>
              <Btn tone="rose" busy={busy} onClick={() => void remove(item.id)} title={t('remove')}>
                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                {armed === item.id ? t('remove_confirm') : null}
              </Btn>
            </div>
          }
        >
          {editing === item.id ? (
            <form
              className="flex gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                void save(item.id);
              }}
            >
              <input className={inputClass} value={draft} maxLength={80} aria-label={t('rename')} autoFocus onChange={(event) => setDraft(event.target.value)} />
              <Btn type="submit" tone="emerald" busy={busy} disabled={draft.trim().length === 0}>
                <Check className="h-3.5 w-3.5" aria-hidden="true" />
              </Btn>
            </form>
          ) : (
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-medium text-slate-900">{item.name}</span>
                {item.id === defaultId ? <Pill tone="amber">{t('default')}</Pill> : null}
              </div>
              <div className="truncate text-xs text-slate-500">{item.detail || `${item.lat.toFixed(2)}, ${item.lon.toFixed(2)}`}</div>
            </div>
          )}
        </Row>
      ))}
    </List>
  );
};
