import React, { useState } from 'react';
import { Music2, Sparkles, Trash2 } from 'lucide-react';
import { Btn, cx, inputClass } from './ui';
import type { Studio } from '../useStudio';

interface Props {
  readonly studio: Studio;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

const IDEAS = ['idea_blues', 'idea_lofi', 'idea_latin', 'idea_epic'];

export const Sidebar: React.FC<Props> = ({ studio, t }) => {
  const [prompt, setPrompt] = useState('');
  const submit = (value: string) => {
    const clean = value.trim();
    if (clean.length >= 3 && !studio.busy) {
      void studio.create(clean);
      setPrompt('');
    }
  };
  return (
    <aside className="flex w-64 shrink-0 flex-col gap-3 border-r border-slate-200 bg-slate-50/70 p-3">
      <div className="rounded-2xl bg-gradient-to-br from-violet-600 via-fuchsia-600 to-rose-500 p-[1px] shadow-sm">
        <div className="rounded-2xl bg-white p-3">
          <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-violet-700">
            <Sparkles size={14} />
            {t('compose_title')}
          </div>
          <textarea
            value={prompt}
            maxLength={500}
            rows={4}
            aria-label={t('compose_title')}
            placeholder={t('compose_placeholder')}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit(prompt);
            }}
            className={cx(inputClass, 'w-full resize-none')}
          />
          <Btn tone="accent" className="mt-2 w-full" disabled={studio.busy || prompt.trim().length < 3} onClick={() => submit(prompt)}>
            <Music2 size={14} />
            {t('compose_go')}
          </Btn>
          <div className="mt-2 flex flex-wrap gap-1">
            {IDEAS.map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => submit(t(key))}
                className="rounded-full bg-violet-50 px-2 py-0.5 text-[11px] text-violet-700 transition hover:bg-violet-100"
              >
                {t(`${key}_label`)}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="px-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t('projects')}</div>
      <ul className="-mx-1 flex-1 space-y-1 overflow-y-auto px-1">
        {studio.summaries.length === 0 && <li className="px-2 py-6 text-center text-xs text-slate-400">{t('projects_empty')}</li>}
        {studio.summaries.map((item) => (
          <li key={item.id}>
            <div
              className={cx(
                'group flex items-center gap-2 rounded-xl border px-2.5 py-2 transition',
                studio.project?.id === item.id ? 'border-violet-300 bg-white shadow-sm' : 'border-transparent hover:bg-white',
              )}
            >
              <button type="button" onClick={() => void studio.open(item.id)} className="min-w-0 flex-1 text-left">
                <div className="truncate text-sm font-medium text-slate-800">{item.title || t('untitled')}</div>
                <div className="truncate text-[11px] capitalize text-slate-500">
                  {item.genre.replace(/_/g, ' ')} · {Math.round(item.tempo)} BPM · {item.tracks} {t('tracks_short')}
                </div>
              </button>
              <button
                type="button"
                aria-label={t('delete')}
                onClick={() => window.confirm(t('delete_confirm')) && void studio.remove(item.id)}
                className="rounded-md p-1 text-slate-300 opacity-0 transition hover:bg-rose-50 hover:text-rose-500 group-hover:opacity-100 focus:opacity-100"
              >
                <Trash2 size={13} />
              </button>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
};
