import React, { useMemo, useState } from 'react';
import { Binary, Cable, Search, Wrench } from 'lucide-react';
import { Empty, OSFilterTabs, Pill, inputClass } from '../../shared/kit';
import { Catalog, CatalogEntry, EntryKind } from '../types';
import { EntryDetail } from './EntryDetail';

interface CatalogTabProps {
  readonly catalog: Catalog;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly onChanged: () => void;
}

const ICONS: Record<EntryKind, React.ReactNode> = {
  skill: <Binary className="h-4 w-4 text-purple-700" aria-hidden="true" />,
  tool: <Wrench className="h-4 w-4 text-amber-700" aria-hidden="true" />,
  connector: <Cable className="h-4 w-4 text-blue-700" aria-hidden="true" />
};

export const CatalogTab: React.FC<CatalogTabProps> = ({ catalog, t, onChanged }) => {
  const [kind, setKind] = useState('all');
  const [filter, setFilter] = useState('');
  const [selected, setSelected] = useState('');

  const rows = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    return catalog.entries.filter(
      (entry) => (kind === 'all' || entry.kind === kind) && (!needle || `${entry.name} ${entry.description} ${entry.group}`.toLowerCase().includes(needle))
    );
  }, [catalog.entries, kind, filter]);

  const current: CatalogEntry | undefined = catalog.entries.find((entry) => entry.key === selected);
  const total = catalog.entries.length;

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <section className="flex min-w-0 flex-col gap-3" aria-label={t('catalog_title')}>
        <OSFilterTabs
          ariaLabel={t('catalog_title')}
          selected={kind}
          onSelect={setKind}
          options={[
            { id: 'all', label: t('kind_all'), count: total },
            { id: 'skill', label: t('kind_skill'), count: catalog.counts.skill },
            { id: 'tool', label: t('kind_tool'), count: catalog.counts.tool },
            { id: 'connector', label: t('kind_connector'), count: catalog.counts.connector }
          ]}
        />
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
          <input className={`${inputClass} pl-9`} value={filter} placeholder={t('search')} aria-label={t('search')} onChange={(event) => setFilter(event.target.value)} />
        </div>
        {rows.length === 0 ? (
          <Empty>{t('empty')}</Empty>
        ) : (
          <ul className="flex flex-col gap-2">
            {rows.map((entry) => (
              <li key={entry.key}>
                <button
                  type="button"
                  onClick={() => setSelected(entry.key)}
                  aria-pressed={entry.key === selected}
                  className={`flex w-full items-start gap-3 rounded-xl border px-3 py-2 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${entry.key === selected ? 'border-cyan-500/60 bg-cyan-500/10' : 'border-slate-800 bg-slate-900/60 hover:border-slate-400'}`}
                >
                  <span className="mt-0.5 shrink-0">{ICONS[entry.kind]}</span>
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <b className="break-all text-sm text-slate-900">{entry.name}</b>
                      <Pill>{entry.group}</Pill>
                      {entry.source !== 'system' ? <Pill tone="cyan">{t(`source_${entry.source}`)}</Pill> : null}
                      {!entry.enabled ? <Pill tone="rose">{t('off')}</Pill> : null}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-600">{entry.description}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
      <div className="min-w-0">
        {current ? (
          <EntryDetail key={current.key} entry={current} t={t} onChanged={onChanged} onRemoved={() => setSelected('')} />
        ) : (
          <Empty>{t('select_hint')}</Empty>
        )}
      </div>
    </div>
  );
};
