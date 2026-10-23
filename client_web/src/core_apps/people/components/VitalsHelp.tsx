import React from 'react';
import { LifeBuoy } from 'lucide-react';
import { VitalsState } from '../data/connectorsApi';
import { usePeopleI18n } from '../scope';

interface Props {
  readonly state: VitalsState;
}

const STEPS = [1, 2, 3, 4, 5];

export const VitalsHelp: React.FC<Props> = ({ state }) => {
  const { t } = usePeopleI18n();
  const stuck = state.devices.some((d) => d.kind === 'ble' && (d.state === 'waiting' || d.state === 'seen'));
  if (!stuck && state.reasons.length === 0) {
    return null;
  }
  return (
    <details className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950" open={state.reasons.length > 0}>
      <summary className="flex cursor-pointer items-center gap-2 font-semibold">
        <LifeBuoy className="h-4 w-4" aria-hidden="true" />
        {t('vh_title')}
      </summary>
      <div className="mt-2 flex flex-col gap-2 text-xs">
        {state.reasons.length > 0 && (
          <ul className="list-disc space-y-1 pl-5 font-semibold">
            {state.reasons.map((reason) => (
              <li key={reason}>{t(`vh_reason_${reason}`, { error: state.reasonError })}</li>
            ))}
          </ul>
        )}
        <p>{t('vh_checklist')}</p>
        <ol className="list-decimal space-y-1 pl-5">
          {STEPS.map((n) => (
            <li key={n}>{t(`vh_step_${n}`)}</li>
          ))}
        </ol>
        <a href="https://support.google.com/fitbit" target="_blank" rel="noopener noreferrer" className="self-start font-semibold underline">
          {t('vh_link')}
        </a>
      </div>
    </details>
  );
};
