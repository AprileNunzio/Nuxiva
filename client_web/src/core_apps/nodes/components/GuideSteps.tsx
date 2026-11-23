import React from 'react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';

export const GuideSteps: React.FC<{ readonly prefix: string; readonly count: number; readonly titleKey?: string }> = ({
  prefix,
  count,
  titleKey,
}) => {
  const { t } = useScopedI18n('core_apps/nodes');
  return (
    <div className="flex flex-col gap-2">
      {titleKey && <h4 className="text-sm font-semibold text-on-surface">{t(titleKey)}</h4>}
      <ol className="flex flex-col gap-2">
        {Array.from({ length: count }, (_, index) => (
          <li key={index} className="flex gap-3 text-sm text-on-surface">
            <span className="md-glyph h-6 w-6 shrink-0 text-xs font-bold" aria-hidden="true">{index + 1}</span>
            <span className="min-w-0">{t(`${prefix}_step_${index + 1}`)}</span>
          </li>
        ))}
      </ol>
    </div>
  );
};
