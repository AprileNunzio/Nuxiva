import React, { useState } from 'react';
import { Pause, Play, Archive } from 'lucide-react';
import { Btn } from '../../shared/kit';
import { bulkState } from '../api';
import { errorKey, useFleetI18n } from '../scope';
import { FleetFilters } from '../types';

interface Props {
  readonly filters: FleetFilters;
  readonly onDone: () => void;
}

const ACTIONS = [
  { state: 'active', Icon: Play, tone: 'emerald' },
  { state: 'paused', Icon: Pause, tone: 'amber' },
  { state: 'archived', Icon: Archive, tone: 'slate' },
] as const;

export const BulkBar: React.FC<Props> = ({ filters, onDone }) => {
  const { t } = useFleetI18n();
  const [armed, setArmed] = useState('');
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');

  const apply = async (state: string) => {
    if (armed !== state) {
      setArmed(state);
      setNote('');
      return;
    }
    setBusy(true);
    try {
      const outcome = await bulkState(filters, state);
      setNote(outcome.more ? t('bulk_more', { n: outcome.changed }) : t('bulk_done', { n: outcome.changed }));
      onDone();
    } catch (cause) {
      setNote(t(errorKey(cause)));
    } finally {
      setBusy(false);
      setArmed('');
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label={t('bulk_title')}>
      <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">{t('bulk_title')}</span>
      {ACTIONS.map(({ state, Icon, tone }) => (
        <Btn key={state} tone={tone} busy={busy} onClick={() => void apply(state)}>
          <Icon className="h-3.5 w-3.5" aria-hidden="true" />
          {armed === state ? t('bulk_confirm') : t(`bulk_${state}`)}
        </Btn>
      ))}
      {note ? <span role="status" className="text-xs text-slate-400">{note}</span> : null}
    </div>
  );
};
