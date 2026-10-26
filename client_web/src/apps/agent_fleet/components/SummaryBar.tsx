import React from 'react';
import { Stat, StatRow } from '../../shared/kit';
import { useFleetI18n } from '../scope';
import { FleetSummary } from '../types';

const format = (value: number, locale: string) => new Intl.NumberFormat(locale, { notation: value >= 1_000_000 ? 'compact' : 'standard' }).format(value);

export const SummaryBar: React.FC<{ readonly summary: FleetSummary | null }> = ({ summary }) => {
  const { t, lang } = useFleetI18n();
  const count = (key: string) => format(summary?.state[key] ?? 0, lang);
  return (
    <StatRow>
      <Stat label={t('stat_total')} value={format(summary?.total ?? 0, lang)} />
      <Stat label={t('stat_active')} value={count('active')} tone="emerald" />
      <Stat label={t('stat_paused')} value={count('paused')} tone="amber" />
      <Stat label={t('stat_archived')} value={count('archived')} tone="slate" />
      <Stat label={t('stat_shards')} value={`${summary?.shards_used ?? 0}/${summary?.shards ?? 0}`} tone="purple" />
    </StatRow>
  );
};
