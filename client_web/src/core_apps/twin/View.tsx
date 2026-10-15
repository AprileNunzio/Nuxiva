import React from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/twin');
  return (
    <div className="p-6 text-slate-100 font-mono">
      <h1 className="text-xl font-bold text-cyan-400">{t('title')}</h1>
      <p className="text-sm text-slate-400 mt-2">{t('description')}</p>
    </div>
  );
};
