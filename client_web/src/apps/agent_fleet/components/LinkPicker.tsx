import React, { useEffect, useState } from 'react';
import { Plus, X } from 'lucide-react';
import { Btn, Empty } from '../../shared/kit';
import { fetchCatalog } from '../api';
import { fieldClass, useFleetI18n } from '../scope';
import { CatalogItem, LinkKind } from '../types';

interface Props {
  readonly kind: LinkKind;
  readonly current: readonly string[];
  readonly missing: readonly string[];
  readonly busy: boolean;
  readonly onAttach: (ref: string) => void;
  readonly onDetach: (ref: string) => void;
}

export const LinkPicker: React.FC<Props> = ({ kind, current, missing, busy, onAttach, onDetach }) => {
  const { t } = useFleetI18n();
  const [query, setQuery] = useState('');
  const [options, setOptions] = useState<readonly CatalogItem[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      fetchCatalog(kind, query, controller.signal)
        .then((page) => setOptions(page.items.filter((item) => !current.includes(item.id))))
        .catch(() => (controller.signal.aborted ? undefined : setOptions([])));
    }, 250);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [kind, query, current]);

  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400">{t(kind === 'tool' ? 'tools' : 'widgets')}</h3>
      {current.length === 0 ? (
        <Empty>{t(kind === 'tool' ? 'no_tools' : 'no_widgets')}</Empty>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {current.map((ref) => (
            <li key={ref} className={`flex items-center gap-1 rounded-lg border px-2 py-1 text-xs ${missing.includes(ref) ? 'border-rose-500/50 text-rose-200' : 'border-slate-700 text-slate-200'}`}>
              <span className="font-mono">{ref}</span>
              {missing.includes(ref) ? <span>· {t('missing_link')}</span> : null}
              <button type="button" disabled={busy} onClick={() => onDetach(ref)} aria-label={`${t('detach')} ${ref}`} className="rounded p-0.5 text-slate-400 hover:text-rose-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400">
                <X className="h-3 w-3" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
      <input type="search" className={fieldClass} value={query} maxLength={80} placeholder={t('search_catalog')} aria-label={t('search_catalog')} onChange={(event) => setQuery(event.target.value)} />
      <ul className="flex max-h-40 flex-col gap-1 overflow-y-auto">
        {options.slice(0, 12).map((item) => (
          <li key={item.id} className="flex items-center justify-between gap-2 rounded-lg px-2 py-1 text-xs hover:bg-slate-800/60">
            <span className="min-w-0">
              <span className="font-mono text-slate-200">{item.id}</span>
              <span className="block truncate text-slate-500">{item.description}</span>
            </span>
            <Btn busy={busy} onClick={() => onAttach(item.id)} title={t('attach')}>
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            </Btn>
          </li>
        ))}
      </ul>
    </section>
  );
};
