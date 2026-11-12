import React, { useState } from 'react';
import { AppFrame, Empty, Loading, Panel, Unreachable } from '../shared/kit';
import { useResource } from '../shared/useResource';
import { Detail } from './Detail';
import { KNOWN_LEVELS, useFascicoliI18n } from './scope';
import type { FascicoloItem } from './types';

const LIMIT = 50;
const URL = `/api/fascicoli?limit=${LIMIT}`;

export const View: React.FC = () => {
  const { t, lang } = useFascicoliI18n();
  const [selected, setSelected] = useState('');
  const list = useResource<{ readonly items: readonly FascicoloItem[] }>(URL, 15000);
  const items = list.dataUrl === URL ? list.data?.items ?? [] : [];

  if (list.error && !list.data) {
    return <Unreachable label={t('unreachable')} />;
  }

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={list.reload}>
      <div className={`grid gap-4 ${selected ? 'lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]' : ''}`}>
        <Panel title={t('list_title')}>
          {list.loading && items.length === 0 ? (
            <Loading label={t('loading')} />
          ) : items.length === 0 ? (
            <Empty>{t('empty')}</Empty>
          ) : (
            <ul className="flex flex-col gap-2">
              {items.map((item) => (
                <li key={item.rel}>
                  <button
                    type="button"
                    onClick={() => setSelected(item.rel === selected ? '' : item.rel)}
                    aria-pressed={item.rel === selected}
                    className="md-state w-full rounded-2xl border border-outline px-3 py-2 text-left"
                  >
                    <span className="flex flex-wrap items-center justify-between gap-2 text-xs text-on-surface-variant">
                      <span>{new Date(item.created).toLocaleString(lang)}</span>
                      <span>
                        {KNOWN_LEVELS.has(item.level) ? t(`level_${item.level}`) : t('level_unknown')} · {t(item.closed ? 'status_closed' : 'status_open')}
                        {item.checked ? ` · ${t('status_checked')}` : ''}
                      </span>
                    </span>
                    <span className="mt-1 block truncate text-sm font-medium">{item.request || item.id}</span>
                    {item.agents && <span className="block truncate text-xs text-on-surface-variant">{item.agents}</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Panel>
        {selected && <Detail key={selected} rel={selected} />}
      </div>
      <p className="mt-3 text-xs text-on-surface-variant">{t('privacy_hint')}</p>
    </AppFrame>
  );
};
