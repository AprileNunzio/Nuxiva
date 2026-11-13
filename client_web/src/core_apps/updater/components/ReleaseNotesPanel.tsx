import React from 'react';
import { Bug, Sparkles } from 'lucide-react';
import type { LocalizedText, ReleaseNotesReport } from '../types';
import { formatDay, labelClass, mutedClass, panelClass, useUpdaterI18n } from '../scope';

const COMPACT_LIMIT = 6;

export function pickText(text: LocalizedText, lang: string): string {
  const key = lang.slice(0, 2).toLowerCase() as keyof LocalizedText;
  return text[key] || text.en || text.it || '';
}

interface GroupProps {
  readonly kind: 'features' | 'fixes';
  readonly items: readonly LocalizedText[];
  readonly limit?: number;
}

const NoteGroup: React.FC<GroupProps> = ({ kind, items, limit }) => {
  const { t, lang } = useUpdaterI18n();
  if (items.length === 0) return null;
  const shown = limit ? items.slice(0, limit) : items;
  const Icon = kind === 'features' ? Sparkles : Bug;
  const tone = kind === 'features' ? 'text-[var(--md-sys-color-primary)]' : 'text-emerald-500';
  return (
    <div className="min-w-0">
      <h3 className={`mb-2 inline-flex items-center gap-2 font-mono text-[11px] font-semibold uppercase tracking-[0.16em] ${tone}`}>
        <Icon className="h-3.5 w-3.5" aria-hidden="true" />
        {t(`notes_${kind}`)}
        <span className={mutedClass}>{items.length}</span>
      </h3>
      <ul className="flex flex-col gap-1.5">
        {shown.map((item, index) => (
          <li key={index} className="upd-note-item grid gap-2 text-sm leading-relaxed text-[var(--md-sys-color-on-surface)]">
            <span className={`${tone} select-none`} aria-hidden="true">•</span>
            <span className="min-w-0 break-words">{pickText(item, lang)}</span>
          </li>
        ))}
      </ul>
      {shown.length < items.length && (
        <p className={`mt-1.5 text-xs ${mutedClass}`}>{t('notes_more', { count: items.length - shown.length })}</p>
      )}
    </div>
  );
};

interface PanelProps {
  readonly report: ReleaseNotesReport | null | undefined;
  readonly compact?: boolean;
}

export const ReleaseNotesPanel: React.FC<PanelProps> = ({ report, compact = false }) => {
  const { t, lang } = useUpdaterI18n();
  const notes = report?.notes ?? [];
  const rejected = report?.rejected.length ?? 0;
  if (compact && notes.length === 0) return null;
  return (
    <section className={panelClass} aria-labelledby={compact ? 'upd-notes-compact' : 'upd-notes-title'}>
      <h2 id={compact ? 'upd-notes-compact' : 'upd-notes-title'} className={labelClass}>
        {t('notes_title')}
        {notes.length > 0 && <span className={`ml-2 normal-case tracking-normal ${mutedClass}`}>{t('notes_summary', { features: report?.features ?? 0, fixes: report?.fixes ?? 0 })}</span>}
      </h2>
      {notes.length === 0 && <p className={`text-sm ${mutedClass}`}>{t('notes_empty')}</p>}
      {compact ? (
        <div className="upd-notes-grid grid gap-6">
          <NoteGroup kind="features" items={notes.flatMap((note) => note.features)} limit={COMPACT_LIMIT} />
          <NoteGroup kind="fixes" items={notes.flatMap((note) => note.fixes)} limit={COMPACT_LIMIT} />
        </div>
      ) : (
        <ol className="flex flex-col gap-6">
          {notes.map((note) => (
            <li key={note.id} className="flex flex-col gap-3">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <span className={`font-mono text-[11px] ${mutedClass}`}>{formatDay(note.date, lang)}</span>
                <p className="min-w-0 break-words text-base font-semibold text-[var(--md-sys-color-on-surface)]">{pickText(note.title, lang)}</p>
              </div>
              <div className="upd-notes-grid grid gap-6">
                <NoteGroup kind="features" items={note.features} />
                <NoteGroup kind="fixes" items={note.fixes} />
              </div>
            </li>
          ))}
        </ol>
      )}
      {rejected > 0 && <p className="mt-3 text-xs text-amber-500">{t('notes_rejected', { count: rejected })}</p>}
    </section>
  );
};
