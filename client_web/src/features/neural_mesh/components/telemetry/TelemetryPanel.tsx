import React from 'react';
import { X } from 'lucide-react';

interface TelemetryPanelProps {
  readonly docked: boolean;
  readonly closeLabel: string;
  readonly labelledBy: string;
  readonly onClose: () => void;
  readonly children: React.ReactNode;
}

export const TelemetryPanel: React.FC<TelemetryPanelProps> = ({ docked, closeLabel, labelledBy, onClose, children }) => (
  <aside
    aria-labelledby={labelledBy}
    aria-live="polite"
    className={`nm-glass nm-enter absolute z-30 flex flex-col overflow-hidden border border-cyan-400/25 shadow-[0_0_50px_rgba(34,211,238,0.12)] ${
      docked
        ? 'bottom-4 right-4 top-4 w-[22rem] rounded-2xl'
        : 'inset-x-2 bottom-2 max-h-[62%] rounded-2xl md:inset-x-auto md:bottom-4 md:right-4 md:w-[22rem]'
    }`}
  >
    {!docked && (
      <button
        type="button"
        onClick={onClose}
        aria-label={closeLabel}
        className="absolute right-3 top-3 z-10 rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-800 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
      >
        <X className="h-4 w-4" aria-hidden="true" />
      </button>
    )}
    <div className="custom-scrollbar flex-1 overflow-y-auto p-4">{children}</div>
  </aside>
);
