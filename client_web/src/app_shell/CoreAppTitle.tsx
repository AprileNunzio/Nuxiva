import React from 'react';
import { useScopedI18n } from '../shared/i18n/useScopedI18n';

export const CoreAppTitle: React.FC<{ readonly appId: string }> = ({ appId }) => {
  const { t } = useScopedI18n(`core_apps/${appId}`);
  return <>{t('title')}</>;
};
