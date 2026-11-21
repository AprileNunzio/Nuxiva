import React from 'react';
import { ShieldCheck, Monitor, Camera, Mic, AlertTriangle, X } from 'lucide-react';

interface RemoteKioskAdvisoryModalProps {
  isOpen: boolean;
  mandatory?: boolean;
  onClose?: () => void;
  onDecision: (enable: boolean) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

export const RemoteKioskAdvisoryModal: React.FC<RemoteKioskAdvisoryModalProps> = ({
  isOpen,
  mandatory = false,
  onClose,
  onDecision,
  t,
}) => {
  if (!isOpen) return null;

  const handleBackdrop = (event: React.MouseEvent<HTMLDivElement>) => {
    if (mandatory) return;
    if (event.target === event.currentTarget && onClose) {
      onClose();
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="advisory-title"
      onClick={handleBackdrop}
      className="fixed inset-0 z-[200020] flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm sm:p-6"
    >
      <div
        className="relative flex max-h-[92vh] w-full max-w-xl flex-col overflow-hidden rounded-2xl border border-outline-variant/60 bg-surface text-on-surface shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-outline-variant/40 bg-surface-container-high px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-primary">
              <Monitor className="h-5 w-5" />
            </div>
            <div>
              <h2 id="advisory-title" className="text-base font-bold tracking-tight text-on-surface sm:text-lg">
                {t('advisory_title')}
              </h2>
              <p className="text-xs text-on-surface-variant">
                {t('advisory_subtitle')}
              </p>
            </div>
          </div>
          {!mandatory && onClose && (
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1.5 text-on-surface-variant transition hover:bg-surface-container hover:text-on-surface"
              aria-label={t('advisory_close')}
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-5 sm:p-6">
          <div className="flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3.5 py-2 text-xs font-semibold text-amber-300">
            <ShieldCheck className="h-4 w-4 shrink-0" />
            <span>{t('advisory_security_badge')}</span>
          </div>

          <p className="text-sm leading-relaxed text-on-surface-variant">
            {t('advisory_desc')}
          </p>

          <div className="rounded-xl border border-outline-variant/50 bg-surface-container p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
              <div className="space-y-2">
                <p className="text-xs font-semibold text-on-surface">
                  {t('advisory_media_notice')}
                </p>
                <div className="flex flex-wrap gap-2 pt-1">
                  <span className="inline-flex items-center gap-1.5 rounded-lg bg-surface-container-high px-2.5 py-1 text-[11px] font-medium text-on-surface">
                    <Camera className="h-3.5 w-3.5 text-primary" />
                    Webcam (HTTP & HTTPS)
                  </span>
                  <span className="inline-flex items-center gap-1.5 rounded-lg bg-surface-container-high px-2.5 py-1 text-[11px] font-medium text-on-surface">
                    <Mic className="h-3.5 w-3.5 text-primary" />
                    Microphone (HTTP & HTTPS)
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col-reverse gap-2.5 border-t border-outline-variant/40 bg-surface-container px-5 py-4 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={() => onDecision(false)}
            className="w-full rounded-xl border border-outline-variant bg-surface-container-high px-4 py-2.5 text-xs font-bold text-on-surface transition hover:bg-surface-container-highest focus:outline-none focus-visible:ring-2 focus-visible:ring-primary sm:w-auto"
          >
            {t('advisory_disable_btn')}
          </button>
          <button
            type="button"
            onClick={() => onDecision(true)}
            className="w-full rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-on-primary shadow-xs transition hover:opacity-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary sm:w-auto"
          >
            {t('advisory_enable_btn')}
          </button>
        </div>
      </div>
    </div>
  );
};
