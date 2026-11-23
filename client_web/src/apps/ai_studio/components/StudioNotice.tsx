import React from 'react';
import { useStudioI18n } from '../scope';

interface StudioNoticeProps {
  message: string | null;
  onDismiss: () => void;
}

export const StudioNotice: React.FC<StudioNoticeProps> = ({ message, onDismiss }) => {
  const { t } = useStudioI18n();
  if (!message) return null;
  return (
    <div role="alert" className="mx-3 mt-2 px-3 py-2 rounded-xl border border-rose-700/60 bg-rose-950/60 text-xs text-rose-200 flex items-center justify-between gap-2">
      <span className="min-w-0 break-words">{message}</span>
      <button type="button" onClick={onDismiss} className="shrink-0 underline">{t('dismiss')}</button>
    </div>
  );
};
