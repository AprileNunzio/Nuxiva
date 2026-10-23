import React, { useState } from 'react';
import { Plus, Search } from 'lucide-react';
import { Btn, Empty, List, Row, inputClass } from '../../shared/kit';
import { useAction } from '../../shared/useResource';
import { addPlace, searchPlaces } from '../api';
import { SearchHit } from '../types';

interface Props {
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly onAdded: () => void;
}

export const PlaceSearch: React.FC<Props> = ({ t, onAdded }) => {
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const { busy, run } = useAction();

  const search = async () => {
    if (query.trim().length < 2) return;
    const found = await run(() => searchPlaces(query), 'weather_search_failed');
    setHits(found ?? []);
  };

  const add = async (hit: SearchHit) => {
    const done = await run(() => addPlace(hit, false).then(() => true), 'weather_failed');
    if (done) {
      setHits(null);
      setQuery('');
      onAdded();
    }
  };

  return (
    <div className="grid gap-3">
      <form
        className="flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          void search();
        }}
      >
        <input
          className={inputClass}
          value={query}
          maxLength={80}
          placeholder={t('search_placeholder')}
          aria-label={t('search_placeholder')}
          onChange={(event) => setQuery(event.target.value)}
        />
        <Btn type="submit" busy={busy} disabled={query.trim().length < 2}>
          <Search className="h-3.5 w-3.5" aria-hidden="true" />
          {t('search')}
        </Btn>
      </form>
      {hits === null ? null : hits.length === 0 ? (
        <Empty>{t('search_empty')}</Empty>
      ) : (
        <List>
          {hits.map((hit) => (
            <Row
              key={`${hit.lat}:${hit.lon}`}
              actions={
                <Btn tone="emerald" busy={busy} onClick={() => void add(hit)}>
                  <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                  {t('add')}
                </Btn>
              }
            >
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-slate-100">{hit.name}</div>
                <div className="truncate text-xs text-slate-500">{hit.detail}</div>
              </div>
            </Row>
          ))}
        </List>
      )}
    </div>
  );
};
