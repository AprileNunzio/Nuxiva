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
    <div className="fixed inset-0 z-[70] flex items-end justify-center bg-black/70 backdrop-blur-sm sm:items-center sm:p-4">
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-body"
        className={`w-full max-w-md rounded-t-2xl border bg-slate-950/95 p-5 shadow-2xl sm:rounded-2xl ${
          danger ? 'border-rose-500/40 shadow-rose-500/10' : 'border-cyan-400/30'
        }`}
      >
        <div className="flex items-start gap-3">
          <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${danger ? 'bg-rose-500/15' : 'bg-cyan-400/10'}`}>
            <AlertTriangle className={`h-5 w-5 ${danger ? 'text-rose-300' : 'text-cyan-200'}`} aria-hidden="true" />
          </span>
          <div>
            <h2 id="confirm-dialog-title" className="font-['Rajdhani'] text-lg font-bold tracking-wide text-white">
              {title}
            </h2>
            <p id="confirm-dialog-body" className="mt-1 text-sm leading-relaxed text-slate-300">
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
            className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm text-slate-300 transition hover:bg-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={pending}
            className={`flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-bold transition disabled:opacity-60 focus:outline-none focus-visible:ring-2 ${
              danger ? 'bg-rose-500 text-white hover:bg-rose-400 focus-visible:ring-rose-200' : 'bg-cyan-400 text-slate-950 hover:bg-cyan-300 focus-visible:ring-cyan-100'
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
