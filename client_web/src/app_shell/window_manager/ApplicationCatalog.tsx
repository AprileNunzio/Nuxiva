import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CircleDot, Grid2X2, Layers, RotateCcw, Search, X, Monitor, Trash2 } from 'lucide-react';
import { OSIcon3D } from '../OSIcon3D';
import { useWindowToolbar } from './WindowContext';
import { useDesktopShortcuts } from '../desktopShortcuts';
import './catalog.css';

export interface CatalogItem {
  id: string;
  label: string;
  description?: string;
  category: string;
  icon?: string;
  symbol?: string;
  active?: boolean;
}

export interface CatalogLabels {
  search: string;
  clearSearch: string;
  categories: string;
  all: string;
  empty: string;
  emptyHint: string;
  stateFilter: string;
  allStates: string;
  on: string;
  off: string;
  reset: string;
  pinToDesktop?: string;
  unpinFromDesktop?: string;
  open?: string;
}

export function ApplicationCatalog({
  items,
  categories,
  lang,
  labels,
  onOpen,
}: {
  items: CatalogItem[];
  categories: Record<string, string>;
  lang: string;
  labels: CatalogLabels;
  onOpen: (id: string) => void;
}) {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [state, setState] = useState('all');
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; itemId: string } | null>(null);

  const { isPinned, togglePin } = useDesktopShortcuts();
  const results = useRef<HTMLDivElement>(null);

  useWindowToolbar((id, value) => {
    if (id === 'search') setSearch(value || '');
  });

  const collator = useMemo(() => new Intl.Collator(lang, { numeric: true, sensitivity: 'base' }), [lang]);
  const normalize = (text: string) => text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase(lang);
  const ordered = useMemo(() => [...items].sort((a, b) => collator.compare(a.label, b.label)), [items, collator]);
  const available = [...new Set(items.map((item) => item.category))].sort((a, b) =>
    collator.compare(categories[a] || a, categories[b] || b)
  );

  const current = available.includes(category) ? category : '';

  useEffect(() => {
    results.current?.scrollTo({ top: 0 });
  }, [current, search, state]);

  useEffect(() => {
    const close = () => setContextMenu(null);
    window.addEventListener('click', close);
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') setContextMenu(null);
    });
    return () => {
      window.removeEventListener('click', close);
    };
  }, []);

  const matches = ordered.filter(
    (item) =>
      (state === 'all' || item.active === (state === 'on')) &&
      normalize(`${item.label} ${item.description || ''}`).includes(normalize(search))
  );
  const visible = matches.filter((item) => !current || item.category === current);
  const count = (value: number) => new Intl.NumberFormat(lang).format(value);
  const reset = () => {
    setCategory('');
    setSearch('');
    setState('all');
  };

  const handleContextMenu = (e: React.MouseEvent, itemId: string) => {
    e.preventDefault();
    e.stopPropagation();
    const rect = e.currentTarget.getBoundingClientRect();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      itemId,
    });
  };

  const pinLabel = labels.pinToDesktop || (lang === 'it' ? 'Aggiungi al Desktop' : 'Add to Desktop');
  const unpinLabel = labels.unpinFromDesktop || (lang === 'it' ? 'Rimuovi dal Desktop' : 'Remove from Desktop');
  const openLabel = labels.open || (lang === 'it' ? 'Apri' : 'Open');

  return (
    <div className="os-catalog relative" onClick={() => setContextMenu(null)}>
      <aside className="os-catalog-sidebar">
        <nav aria-label={labels.categories}>
          <button aria-current={!current ? 'page' : undefined} onClick={() => setCategory('')}>
            <Grid2X2 />
            <span>{labels.all}</span>
            <small>{count(matches.length)}</small>
          </button>
          {available.map((id) => (
            <button key={id} aria-current={current === id ? 'page' : undefined} onClick={() => setCategory(id)}>
              <Layers />
              <span>{categories[id] || id}</span>
              <small>{count(matches.filter((item) => item.category === id).length)}</small>
            </button>
          ))}
        </nav>
        <div className="os-catalog-state">
          <label>
            <CircleDot />
            {labels.stateFilter}
            <select aria-label={labels.stateFilter} value={state} onChange={(event) => setState(event.target.value)}>
              <option value="all">{labels.allStates}</option>
              <option value="on">{labels.on}</option>
              <option value="off">{labels.off}</option>
            </select>
          </label>
        </div>
      </aside>
      <div className="os-catalog-main">
        <div className="os-catalog-tools">
          <label>
            <Search aria-hidden="true" />
            <input
              type="search"
              aria-label={labels.search}
              placeholder={labels.search}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            {search && (
              <button aria-label={labels.clearSearch} onClick={() => setSearch('')}>
                <X />
              </button>
            )}
          </label>
          {(search || current || state !== 'all') && (
            <button className="os-catalog-reset" title={labels.reset} aria-label={labels.reset} onClick={reset}>
              <RotateCcw />
            </button>
          )}
        </div>
        <div className="os-catalog-heading">
          <strong>{current ? categories[current] || current : labels.all}</strong>
          <span role="status" aria-live="polite">
            {count(visible.length)}
          </span>
        </div>
        <div className="os-catalog-results" ref={results}>
          {visible.length === 0 ? (
            <div className="os-catalog-empty" role="status">
              <Search />
              <strong>{labels.empty}</strong>
              <p>{labels.emptyHint}</p>
              <button onClick={reset}>{labels.reset}</button>
            </div>
          ) : (
            <section className="os-catalog-group">
              <div>
                {visible.map((item) => (
                  <button
                    key={item.id}
                    title={item.description || item.label}
                    onClick={() => onOpen(item.id)}
                    onContextMenu={(e) => handleContextMenu(e, item.id)}
                  >
                    {item.icon ? (
                      <OSIcon3D name={item.label} source={item.icon} />
                    ) : (
                      <span className="os-catalog-symbol" aria-hidden="true">
                        {item.symbol || item.label.slice(0, 1)}
                      </span>
                    )}
                    <span>{item.label}</span>
                    {item.active !== undefined && (
                      <i
                        data-active={item.active}
                        title={item.active ? labels.on : labels.off}
                        aria-label={item.active ? labels.on : labels.off}
                      />
                    )}
                  </button>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>

      {/* Context Menu col tasto destro per Aggiungere / Rimuovere dal Desktop */}
      {contextMenu && (
        <div
          className="os-context-menu fixed z-50 bg-slate-900 border border-slate-700/80 rounded-xl shadow-2xl py-1 px-1 text-xs text-slate-200"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          role="menu"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            role="menuitem"
            className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 hover:bg-cyan-500/20 hover:text-cyan-300 transition"
            onClick={() => {
              onOpen(contextMenu.itemId);
              setContextMenu(null);
            }}
          >
            <Monitor className="h-3.5 w-3.5 text-cyan-400" />
            <span>{openLabel}</span>
          </button>
          <button
            role="menuitem"
            className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 hover:bg-cyan-500/20 hover:text-cyan-300 transition"
            onClick={() => {
              togglePin(contextMenu.itemId);
              setContextMenu(null);
            }}
          >
            {isPinned(contextMenu.itemId) ? (
              <>
                <Trash2 className="h-3.5 w-3.5 text-rose-400" />
                <span className="text-rose-300">{unpinLabel}</span>
              </>
            ) : (
              <>
                <Monitor className="h-3.5 w-3.5 text-emerald-400" />
                <span>{pinLabel}</span>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
