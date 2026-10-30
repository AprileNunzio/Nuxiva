import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CheckCircle2, CircleSlash, Plus, Search, X } from 'lucide-react';
import { REF } from '../core/parse';
import { matches } from '../core/format';
import { useBrainText } from '../core/i18n';
import { BrainRef, Origin } from '../core/types';
import { Badge, Button, IconButton, fieldClass } from './primitives';

interface ModelPickerProps {
  readonly title: string;
  readonly pool: readonly BrainRef[];
  readonly exclude: readonly string[];
  readonly onPick: (ref: string) => void;
  readonly onClose: () => void;
}

const ORDER: readonly Origin[] = ['local', 'lan', 'server', 'cloud'];

export const ModelPicker: React.FC<ModelPickerProps> = ({ title, pool, exclude, onPick, onClose }) => {
  const { t } = useBrainText();
  const [query, setQuery] = useState('');
  const [manual, setManual] = useState('');
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    searchRef.current?.focus();
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const groups = useMemo(() => {
    const visible = pool.filter((r) => !exclude.includes(r.ref) && matches(query, r.model, r.provider, r.ref));
    return ORDER.map((origin) => ({ origin, items: visible.filter((r) => r.origin === origin) })).filter((g) => g.items.length > 0);
  }, [pool, exclude, query]);

  const manualRef = manual.trim();
  const manualValid = REF.test(manualRef) && !exclude.includes(manualRef);

  return (
    <div className="fixed inset-0 z-[70] flex items-end justify-center bg-slate-900/40 backdrop-blur-[2px] sm:items-center sm:p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div role="dialog" aria-modal="true" aria-labelledby="brain-picker-title" className="flex max-h-[88vh] w-full max-w-xl flex-col overflow-hidden rounded-t-2xl border border-slate-200 bg-white shadow-2xl sm:rounded-2xl">
        <header className="flex items-center gap-3 border-b border-slate-100 px-4 py-3">
          <h3 id="brain-picker-title" className="min-w-0 flex-1 truncate text-base font-semibold text-slate-900">{title}</h3>
          <IconButton icon={X} label={t('close')} onClick={onClose} />
        </header>
        <div className="border-b border-slate-100 px-4 py-3">
          <label className="relative block">
            <span className="sr-only">{t('search_models')}</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input ref={searchRef} value={query} maxLength={80} onChange={(e) => setQuery(e.target.value)} placeholder={t('search_models')} className={`${fieldClass} pl-9`} />
          </label>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
          {groups.length === 0 && <p className="px-3 py-6 text-center text-sm text-slate-500">{t('no_models_found')}</p>}
          {groups.map((group) => (
            <div key={group.origin} className="mb-2">
              <p className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">{t(`origin_group_${group.origin}`)}</p>
              <ul>
                {group.items.map((item) => (
                  <li key={item.ref}>
                    <button
                      type="button"
                      disabled={!item.available}
                      onClick={() => onPick(item.ref)}
                      className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition hover:bg-blue-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {item.available ? <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" /> : <CircleSlash className="h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />}
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-slate-900">{item.model}</span>
                        <span className="block truncate text-xs text-slate-500">{item.provider || t(`origin_${item.origin}`)}</span>
                      </span>
                      {!item.available && <Badge>{t('unavailable')}</Badge>}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <footer className="flex flex-col gap-2 border-t border-slate-100 bg-slate-50 px-4 py-3 sm:flex-row sm:items-center">
          <label className="min-w-0 flex-1">
            <span className="sr-only">{t('manual_model')}</span>
            <input value={manual} maxLength={230} onChange={(e) => setManual(e.target.value)} placeholder={t('manual_model_placeholder')} className={`${fieldClass} font-mono text-xs`} />
          </label>
          <Button icon={Plus} disabled={!manualValid} onClick={() => onPick(manualRef)}>
            {t('manual_model_add')}
          </Button>
        </footer>
      </div>
    </div>
  );
};
