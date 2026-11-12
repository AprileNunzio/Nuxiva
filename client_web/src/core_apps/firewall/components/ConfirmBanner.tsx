import React, { useEffect, useState } from 'react';
import { ShieldAlert } from 'lucide-react';
import { Btn } from '../../shared/kit';

interface ConfirmBannerProps {
  readonly deadline: number;
  readonly busy: boolean;
  readonly message: string;
  readonly keep: string;
  readonly undo: string;
  readonly onConfirm: () => void;
  readonly onRollback: () => void;
}

export const ConfirmBanner: React.FC<ConfirmBannerProps> = ({ deadline, busy, message, keep, undo, onConfirm, onRollback }) => {
  const [now, setNow] = useState(() => Date.now() / 1000);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const left = Math.ceil(deadline - now);
  if (!deadline || left <= 0) {
    return null;
  }
  return (
    <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <span className="flex items-center gap-2">
        <ShieldAlert className="h-5 w-5" aria-hidden="true" />
        {message.replace('{seconds}', String(left))}
      </span>
      <span className="flex gap-2">
        <Btn tone="emerald" busy={busy} onClick={onConfirm}>
          {keep}
        </Btn>
        <Btn tone="rose" busy={busy} onClick={onRollback}>
          {undo}
        </Btn>
      </span>
    </div>
  );
};
