import React from 'react';
import type { ImpactReport } from '../types';
import { labelClass, mutedClass, panelClass, useUpdaterI18n } from '../scope';

const total = (c: ImpactReport['components'][number]) => c.added + c.modified + c.deleted + c.renamed;

export const ImpactPanel: React.FC<{ readonly impact: ImpactReport | null }> = ({ impact }) => {
  const { t } = useUpdaterI18n();
  const components = impact?.components ?? [];
  const peak = Math.max(1, ...components.map(total));

  return (
    <section className={panelClass} aria-labelledby="upd-impact-title">
      <h2 id="upd-impact-title" className={labelClass}>{t('impact_title')}</h2>
      {!impact || impact.files === 0 ? (
        <p className={`text-sm ${mutedClass}`}>{t('impact_empty')}</p>
      ) : (
        <>
          <p className={`mb-3 font-mono text-xs ${mutedClass}`}>{t('impact_files', { count: impact.files })}</p>
          <ul className="flex flex-col gap-2 font-mono text-xs">
            {components.map((c) => (
              <li key={c.component} className="upd-impact-row grid items-center gap-3">
                <span className="truncate text-[var(--md-sys-color-on-surface)]">{t(`component_${c.component}`)}</span>
                <span className="h-[3px] bg-[var(--md-sys-color-outline-variant)]/50">
                  <span className="block h-full bg-[var(--md-sys-color-primary)]/80" style={{ width: `${(total(c) / peak) * 100}%` }} />
                </span>
                <span className="tabular-nums">
                  <span className="text-emerald-500">+{c.added}</span>{' '}
                  <span className="text-amber-500">~{c.modified + c.renamed}</span>{' '}
                  <span className="text-rose-500">-{c.deleted}</span>
                </span>
              </li>
            ))}
          </ul>
          {impact.effects.length > 0 && (
            <p className={`mt-3 font-mono text-[11px] ${mutedClass}`}>
              {impact.effects.map((effect) => t(`effect_${effect}`)).join(' · ')}
            </p>
          )}
        </>
      )}
    </section>
  );
};
