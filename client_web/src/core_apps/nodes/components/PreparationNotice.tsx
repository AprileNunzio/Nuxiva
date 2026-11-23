import React from 'react';
import { Hourglass } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';

export const PreparationNotice: React.FC<{ readonly prefix: string }> = ({ prefix }) => {
  const { t } = useScopedI18n('core_apps/nodes');
  return (
    <div role="status" className="flex items-start gap-3 rounded-3xl border border-primary/20 bg-primary/5 p-4 text-xs text-on-surface-variant">
      <Hourglass className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
      <div>
        <p className="font-semibold text-primary">{t(`${prefix}_status_title`)}</p>
        <p className="mt-1">{t(`${prefix}_status_desc`)}</p>
      </div>
    </div>
  );
};
