import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useStudioI18n } from '../scope';

export interface PaletteItem {
  id: string;
  label: string;
  group: 'actions' | 'chats';
  hint?: string;
  run: () => void;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  items: PaletteItem[];
}

export const CommandPalette: React.FC<Props> = ({ isOpen, onClose, items }) => {
  const { t } = useStudioI18n();
  const [query, setQuery] = useState('');
  const [index, setIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setIndex(0);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [isOpen]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? items.filter((i) => i.label.toLowerCase().includes(q)) : items;
  }, [items, query]);

  if (!isOpen) return null;

  const choose = (item?: PaletteItem) => {
    if (!item) return;
    onClose();
    item.run();
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
    else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') choose(filtered[index]);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh] bg-black/50 backdrop-blur-sm"
      onClick={onClose}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        className="w-[min(36rem,92vw)] rounded-2xl border border-white/10 bg-slate-900/80 backdrop-blur-xl shadow-[0_0_60px_-15px_rgba(0,240,255,0.35)] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onKeyDown}
      >
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIndex(0);
          }}
          placeholder={t('cmd_placeholder')}
          className="w-full bg-transparent px-5 py-4 text-sm text-slate-100 placeholder-slate-500 outline-none border-b border-white/10"
        />
        <ul className="max-h-80 overflow-y-auto p-2" role="listbox">
          {filtered.length === 0 && (
            <li className="px-3 py-6 text-center text-xs text-slate-500">{t('cmd_empty')}</li>
          )}
          {filtered.map((item, i) => (
            <li
              key={item.id}
              role="option"
              aria-selected={i === index}
              onMouseEnter={() => setIndex(i)}
              onClick={() => choose(item)}
              className={`flex items-center justify-between rounded-xl px-3 py-2 text-sm cursor-pointer transition-colors ${
                i === index ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/10 text-cyan-100' : 'text-slate-300'
              }`}
            >
              <span className="truncate">{item.label}</span>
              <span className="ml-3 text-[10px] uppercase tracking-wider text-slate-500">
                {item.hint || t(item.group === 'actions' ? 'cmd_actions' : 'cmd_chats')}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
