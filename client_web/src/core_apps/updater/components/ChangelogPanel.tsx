import React from 'react';
import { GitCommitHorizontal } from 'lucide-react';
import { panelClass, useUpdaterI18n } from '../scope';

const COMMIT_LINE = /^([0-9a-f]{7,40})\s+(.*)$/i;

export const ChangelogPanel: React.FC<{ readonly entries: readonly string[] }> = ({ entries }) => {
  const { t } = useUpdaterI18n();
  return (
    <section className={panelClass} aria-labelledby="upd-changelog-title">
      <h2 id="upd-changelog-title" className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600">
        {t('changelog_title')}
      </h2>
      {entries.length === 0 ? (
        <p className="text-sm text-slate-500">{t('changelog_empty')}</p>
      ) : (
        <ol className="flex flex-col gap-2">
          {entries.map((line) => {
            const match = COMMIT_LINE.exec(line);
            const [sha, message] = match ? [match[1], match[2]] : ['', line];
            const [primary] = message.split(' | ');
            return (
              <li key={line} className="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
                <GitCommitHorizontal className="mt-0.5 h-4 w-4 shrink-0 text-cyan-700" aria-hidden="true" />
                <div className="min-w-0">
                  <p className="break-words text-sm text-slate-800">{primary}</p>
                  {sha && <p className="font-mono text-[11px] text-slate-500">{sha.slice(0, 7)}</p>}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
};
