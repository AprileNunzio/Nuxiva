import React from 'react';
import { Box, Trash2 } from 'lucide-react';
import type { Summary } from '../types';

interface LibraryProps {
  readonly rows: readonly Summary[];
  readonly t: (key: string) => string;
  readonly onOpen: (id: string) => void;
  readonly onDelete: (id: string) => void;
}

export const Library: React.FC<LibraryProps> = ({ rows, t, onOpen, onDelete }) => {
  if (rows.length === 0) return <p className="py-4 text-center text-xs text-slate-400">{t('library_empty')}</p>;
  return (
    <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {rows.map((row) => (
        <li key={row.id} className="group flex items-center gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm transition hover:border-sky-300 hover:shadow-md">
          <button type="button" onClick={() => onOpen(row.id)} className="flex min-w-0 flex-1 items-center gap-3 text-left">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-sky-100 to-amber-100 text-sky-700"><Box className="h-5 w-5" /></span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-bold text-slate-900">{row.title || t('untitled')}</span>
              <span className="block text-[11px] text-slate-500">{row.count} {t('items')} · {new Date(row.created * 1000).toLocaleDateString()}</span>
            </span>
          </button>
          <button type="button" onClick={() => onDelete(row.id)} aria-label={t('delete')} className="rounded-lg p-2 text-slate-300 transition hover:bg-rose-50 hover:text-rose-600"><Trash2 className="h-4 w-4" /></button>
        </li>
      ))}
    </ul>
  );
};
