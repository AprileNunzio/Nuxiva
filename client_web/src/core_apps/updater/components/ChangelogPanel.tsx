import React from 'react';
import type { ChangeEntry } from '../types';
import { labelClass, mutedClass, panelClass, useUpdaterI18n } from '../scope';

const KIND_TONE: Readonly<Record<string, string>> = {
  feat: 'text-[var(--md-sys-color-primary)]',
  fix: 'text-emerald-500',
  security: 'text-rose-500',
  perf: 'text-amber-500',
};

export const ChangelogPanel: React.FC<{ readonly entries: readonly ChangeEntry[] }> = ({ entries }) => {
  const { t } = useUpdaterI18n();
  return (
    <section className={panelClass} aria-labelledby="upd-changelog-title">
      <h2 id="upd-changelog-title" className={labelClass}>{t('changelog_title')}</h2>
      {entries.length === 0 ? (
        <p className={`text-sm ${mutedClass}`}>{t('changelog_empty')}</p>
      ) : (
        <ol className="flex flex-col divide-y divide-[var(--md-sys-color-outline-variant)]/40">
          {entries.map((entry) => (
            <li key={entry.sha} className="upd-change-row grid gap-x-3 py-2.5">
              <span className={`font-mono text-[11px] uppercase tracking-wider ${KIND_TONE[entry.kind] ?? mutedClass}`}>
                {t(`kind_${entry.kind}`)}{entry.breaking && <span className="text-rose-500"> !</span>}
              </span>
              <p className="min-w-0 break-words text-sm text-[var(--md-sys-color-on-surface)]">
                {entry.scope && <span className={`mr-1.5 font-mono text-xs ${mutedClass}`}>{entry.scope}</span>}
                {entry.summary}
              </p>
              <span className={`upd-change-sha font-mono text-[11px] ${mutedClass}`}>{entry.sha.slice(0, 7)}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
};
