import React, { useEffect, useRef, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { Btn, Panel } from '../../shared/kit';
import { probe } from '../api';
import { ResetReport, Translate } from '../types';

const POLL_MS = 3000;
const GIVE_UP_MS = 15 * 60 * 1000;

interface Props {
  readonly resetId: string;
  readonly onFinished: (report: ResetReport | null) => void;
  readonly t: Translate;
}

export const ProgressStep: React.FC<Props> = ({ resetId, onFinished, t }) => {
  const [phase, setPhase] = useState<'working' | 'down'>('working');
  const [stuck, setStuck] = useState(false);
  const began = useRef(Date.now());

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      const result = await probe();
      if (!alive) return;
      if (result.kind === 'down') {
        setPhase('down');
      } else if (result.kind === 'signed_out') {
        onFinished(null);
      } else if (result.report && result.report.id === resetId) {
        onFinished(result.report);
      } else {
        setPhase('working');
      }
      if (Date.now() - began.current > GIVE_UP_MS) setStuck(true);
    };
    const timer = window.setInterval(() => void tick(), POLL_MS);
    void tick();
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [resetId, onFinished]);

  return (
    <Panel title={t('running_title')}>
      <div className="flex flex-col items-center gap-3 py-8 text-center" role="status" aria-live="polite">
        <Loader2 className="h-8 w-8 animate-spin text-rose-300" aria-hidden="true" />
        <p className="text-sm text-slate-200">{t(phase === 'down' ? 'running_down' : 'running_working')}</p>
        <p className="max-w-md text-xs text-slate-500">{t('running_hint')}</p>
        {stuck ? (
          <Btn tone="slate" onClick={() => onFinished(null)}>
            {t('running_check')}
          </Btn>
        ) : null}
      </div>
    </Panel>
  );
};
