import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

interface DialogProps {
  readonly title: string;
  readonly closeLabel: string;
  readonly onClose: () => void;
  readonly children: React.ReactNode;
}

export const Dialog: React.FC<DialogProps> = ({ title, closeLabel, onClose, children }) => {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    box.current?.querySelector<HTMLElement>('input, select, textarea')?.focus();
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-white p-0 backdrop-blur-sm sm:items-center sm:p-4" role="presentation">
      <div
        ref={box}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-t-2xl border border-slate-300 bg-white p-5 shadow-2xl sm:rounded-2xl"
      >
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="font-['Rajdhani'] text-xl font-bold text-slate-950">{title}</h2>
          <button type="button" onClick={onClose} aria-label={closeLabel} className="rounded-lg p-1.5 text-slate-600 hover:text-slate-950 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400">
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
};
