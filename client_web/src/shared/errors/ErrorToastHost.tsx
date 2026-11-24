import React, { useEffect, useState } from 'react';
import { ReportedError, SERVER_UNREACHABLE, subscribeErrors } from './errorBus';
import { useScopedI18n } from '../i18n/useScopedI18n';
import { ConnectivityToast } from './toasts/ConnectivityToast';
import { ErrorToast } from './toasts/ErrorToast';

const VISIBLE_LIMIT = 3;
const DISMISS_MS = { warning: 20000, critical: 45000 } as const;

export const ErrorToastHost: React.FC = () => {
  const { t, lang } = useScopedI18n('shared/errors');
  const [errors, setErrors] = useState<readonly ReportedError[]>([]);

  useEffect(
    () =>
      subscribeErrors((entry) => {
        if (entry.code === SERVER_UNREACHABLE) return;
        setErrors((current) => [...current, entry].slice(-VISIBLE_LIMIT));
        window.setTimeout(() => {
          setErrors((current) => current.filter((e) => e.id !== entry.id));
        }, DISMISS_MS[entry.severity]);
      }),
    [],
  );

  const dismiss = (id: number) => setErrors((current) => current.filter((e) => e.id !== id));

  return (
    <div
      aria-live="assertive"
      data-tone="dark"
      className="pointer-events-none fixed inset-x-4 bottom-20 z-[200005] flex max-h-[70vh] flex-col items-center gap-2 overflow-y-auto sm:inset-x-auto sm:right-4 sm:items-end"
    >
      <ConnectivityToast t={t} lang={lang} />
      {errors.map((entry) => (
        <ErrorToast key={entry.id} entry={entry} t={t} lang={lang} onDismiss={dismiss} />
      ))}
    </div>
  );
};
