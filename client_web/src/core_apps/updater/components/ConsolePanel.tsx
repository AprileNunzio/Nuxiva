import React, { useEffect, useMemo, useRef } from 'react';
import { formatLine } from '../consoleFormat';
import type { ConsoleLine } from '../types';
import { labelClass, mutedClass, panelClass, tone, useUpdaterI18n } from '../scope';

export const ConsolePanel: React.FC<{ readonly lines: readonly ConsoleLine[] }> = ({ lines }) => {
  const { t } = useUpdaterI18n();
  const viewport = useRef<HTMLDivElement | null>(null);
  const formatted = useMemo(() => lines.map(formatLine), [lines]);

  useEffect(() => {
    const node = viewport.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [formatted.length]);

  return (
    <section className={panelClass} aria-labelledby="upd-console-title">
      <h2 id="upd-console-title" className={labelClass}>{t('console_title')}</h2>
      <div ref={viewport} className="max-h-72 overflow-y-auto pr-1 font-mono text-[11.5px] leading-6" role="log" aria-live="polite">
        {formatted.length === 0 ? (
          <p className={mutedClass}>{t('console_empty')}</p>
        ) : formatted.map((line) => (
          <p key={line.key} className="upd-console-line grid gap-x-3">
            <span className={`tabular-nums ${mutedClass}`}>{line.time}</span>
            <span className={`uppercase ${tone(line.level)}`}>{t(`level_${line.level}`)}</span>
            <span className={`upd-console-stage truncate ${mutedClass}`}>{line.stage ? t(`stage_${line.stage}`) : '—'}</span>
            <span className="min-w-0 break-words text-[var(--md-sys-color-on-surface)]">
              {t(line.messageKey, { ...line.params, stage: line.stage ? t(`stage_${line.stage}`) : '' })}
              {line.detail && <span className={`ml-2 ${mutedClass}`}>{line.detail}</span>}
            </span>
          </p>
        ))}
      </div>
    </section>
  );
};
