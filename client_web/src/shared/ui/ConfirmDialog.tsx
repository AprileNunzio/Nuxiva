import React, { useEffect, useRef } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';

interface ConfirmDialogProps {
  readonly title: string;
  readonly body: string;
  readonly confirmLabel: string;
  readonly cancelLabel: string;
  readonly pending: boolean;
  readonly tone: 'danger' | 'neutral';
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  title,
  body,
  confirmLabel,
  cancelLabel,
  pending,
  tone,
  onConfirm,
  onCancel,
}) => {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    cancelRef.current?.focus();
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && !pending && onCancel();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onCancel, pending]);

  const danger = tone === 'danger';
  return (
    <div className="fixed inset-0 z-[70] flex items-end justify-center bg-slate-900/30 backdrop-blur-sm sm:items-center sm:p-4">
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-body"
        className={`w-full max-w-md rounded-t-2xl border bg-white p-5 shadow-2xl shadow-slate-900/10 sm:rounded-2xl ${
          danger ? 'border-rose-200' : 'border-slate-200'
        }`}
      >
        <div className="flex items-start gap-3">
          <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${danger ? 'bg-rose-50' : 'bg-blue-50'}`}>
            <AlertTriangle className={`h-5 w-5 ${danger ? 'text-rose-600' : 'text-blue-600'}`} aria-hidden="true" />
          </span>
          <div>
            <h2 id="confirm-dialog-title" className="text-lg font-bold tracking-tight text-slate-900">
              {title}
            </h2>
            <p id="confirm-dialog-body" className="mt-1 text-sm leading-relaxed text-slate-600">
              {body}
            </p>
          </div>
        </div>
        <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancel}
            disabled={pending}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={pending}
            className={`flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-bold transition disabled:opacity-60 focus:outline-none focus-visible:ring-2 ${
              danger ? 'bg-rose-600 text-white hover:bg-rose-700 focus-visible:ring-rose-300' : 'bg-blue-600 text-white hover:bg-blue-700 focus-visible:ring-blue-300'
            }`}
          >
            {pending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
