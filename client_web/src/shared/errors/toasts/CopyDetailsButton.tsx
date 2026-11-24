import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { reportError } from '../errorBus';

interface Props {
  readonly payload: () => string;
  readonly label: string;
  readonly doneLabel: string;
}

const DONE_MS = 2000;

export const CopyDetailsButton: React.FC<Props> = ({ payload, label, doneLabel }) => {
  const [done, setDone] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(payload());
      setDone(true);
      window.setTimeout(() => setDone(false), DONE_MS);
    } catch (cause) {
      reportError('clipboard_failed', cause);
    }
  };

  return (
    <button
      type="button"
      onClick={() => void copy()}
      className="inline-flex items-center gap-1 rounded-md border border-slate-600/60 px-2 py-1 text-xs text-slate-200 transition hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
    >
      {done ? <Check className="h-3 w-3" aria-hidden="true" /> : <Copy className="h-3 w-3" aria-hidden="true" />}
      {done ? doneLabel : label}
    </button>
  );
};
