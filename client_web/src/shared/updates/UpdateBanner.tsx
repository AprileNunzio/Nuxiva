import React from 'react';
import { RefreshCw } from 'lucide-react';
import { useScopedI18n } from '../i18n/useScopedI18n';
import { useNewVersion } from './useNewVersion';

export const UpdateBanner: React.FC = () => {
  const { t } = useScopedI18n('shared/updates');
  const { available, seconds, reload, later } = useNewVersion();
  if (!available) {
    return null;
  }
  return (
    <div role="status" aria-live="polite" className="fixed bottom-4 left-1/2 z-[9999] flex max-w-[92vw] -translate-x-1/2 flex-wrap items-center gap-3 rounded-xl border border-sky-300 bg-white px-4 py-3 text-sm text-slate-900 shadow-xl">
      <RefreshCw className="h-4 w-4 animate-spin text-sky-700" aria-hidden="true" />
      <span>{t('new_version', { seconds })}</span>
      <button type="button" onClick={reload} className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-300">
        {t('reload_now')}
      </button>
      <button type="button" onClick={later} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-800 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400">
        {t('later')}
      </button>
    </div>
  );
};
