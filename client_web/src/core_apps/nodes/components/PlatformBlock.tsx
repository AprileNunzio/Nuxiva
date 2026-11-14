import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';

export const PlatformBlock: React.FC<{
  readonly id: string;
  readonly icon: LucideIcon;
  readonly steps: number;
  readonly wide?: boolean;
  readonly children?: React.ReactNode;
}> = ({ id, icon: Icon, steps, wide = false, children }) => {
  const { t } = useScopedI18n('core_apps/nodes');
  return (
    <article className={`flex min-w-0 flex-col gap-3 ${wide ? 'cq-lg:col-span-2' : ''}`} aria-labelledby={`install-${id}`}>
      <header className="flex items-center gap-3">
        <span className="md-glyph h-11 w-11 shrink-0">
          <Icon aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <h3 id={`install-${id}`} className="text-base font-semibold text-on-surface">{t(`install_${id}_title`)}</h3>
          <p className="text-xs text-on-surface-variant">{t(id === 'macos' ? 'install_pending' : 'install_steps_count', { count: steps })}</p>
        </div>
      </header>
      <p className="text-sm text-on-surface-variant">{t(`install_${id}_guide`)}</p>
      <ol className="flex flex-col gap-2">
        {Array.from({ length: steps }, (_, index) => (
          <li key={index} className="flex gap-3 text-sm text-on-surface">
            <span className="md-glyph h-6 w-6 shrink-0 text-xs font-bold" aria-hidden="true">{index + 1}</span>
            <span className="min-w-0">{t(`install_${id}_step_${index + 1}`)}</span>
          </li>
        ))}
      </ol>
      {children}
    </article>
  );
};
