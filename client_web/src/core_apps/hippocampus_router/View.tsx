import React from 'react';
import { Activity, Gauge, ListChecks, SlidersHorizontal } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Empty, List, Loading, Panel, Pill, Row, Stat, StatRow, Tone, Unreachable } from '../shared/kit';
import { useResource } from '../shared/useResource';
import { HippocampusStatus } from './types';

const VERDICT_TONE: Readonly<Record<string, Tone>> = { fast: 'emerald', grey: 'amber', slow: 'purple' };
const THRESHOLD_KEYS = ['fast_similarity', 'grey_similarity', 'inhibition_limit', 'fast_weight', 'grey_weight'] as const;

const percent = (value: number): string => `${Math.round(value * 100)}%`;

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/hippocampus_router');
  const { data, error, loading, reload } = useResource<HippocampusStatus>('/api/v1/cognition/hippocampus/status', 5000);

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const { telemetry } = data;
  const issues = [data.native.error, data.embedding.error, data.storage.error].filter(
    (issue): issue is NonNullable<typeof issue> => issue !== null,
  );

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={reload}>
      <StatRow>
        <Stat label={t('stat_native')} value={data.native.available ? t('on') : t('off')} tone={data.native.available ? 'emerald' : 'rose'} />
        <Stat label={t('stat_embedding')} value={data.embedding.loaded ? t('ready') : t('unavailable')} tone={data.embedding.loaded ? 'emerald' : 'amber'} />
        <Stat label={t('stat_storage')} value={data.storage.persistent ? t('persistent') : t('volatile')} tone={data.storage.persistent ? 'emerald' : 'amber'} />
        <Stat label={t('stat_neurons')} value={data.neurons} tone="purple" />
        <Stat label={t('stat_decisions')} value={telemetry.total} />
        <Stat label={t('stat_latency')} value={`${telemetry.latency_ms.average} ms`} tone="cyan" />
      </StatRow>
      {issues.length > 0 ? (
        <Panel title={t('issues_title')} icon={<Activity className="h-4 w-4 text-amber-300" aria-hidden="true" />}>
          <List>
            {issues.map((issue) => (
              <Row key={issue.code}>
                <span className="font-mono text-[11px] text-slate-500">{issue.code}</span>
                <p className="text-sm">{issue.message}</p>
              </Row>
            ))}
          </List>
        </Panel>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={t('verdicts_title')} icon={<Gauge className="h-4 w-4 text-emerald-300" aria-hidden="true" />}>
          <div className="flex flex-wrap gap-2">
            {(['fast', 'grey', 'slow'] as const).map((verdict) => (
              <Pill key={verdict} tone={VERDICT_TONE[verdict]}>
                {t(`verdict_${verdict}`)}: {telemetry.verdicts[verdict] ?? 0}
              </Pill>
            ))}
          </div>
          <p className="mt-3 text-xs text-slate-500">{t('executed', { n: telemetry.executed })}</p>
          <p className="text-xs text-slate-500">{t('latency_max', { ms: telemetry.latency_ms.maximum })}</p>
          {Object.keys(telemetry.reasons).length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {Object.entries(telemetry.reasons).map(([reason, count]) => (
                <Pill key={reason}>
                  {t(`reason_${reason}`)}: {count}
                </Pill>
              ))}
            </div>
          ) : null}
        </Panel>
        <Panel title={t('thresholds_title')} icon={<SlidersHorizontal className="h-4 w-4 text-cyan-300" aria-hidden="true" />}>
          <List>
            {THRESHOLD_KEYS.map((key) => (
              <Row key={key} actions={<Pill tone="cyan">{percent(data.thresholds[key] ?? 0)}</Pill>}>
                <span className="text-sm">{t(`threshold_${key}`)}</span>
              </Row>
            ))}
          </List>
        </Panel>
      </div>
      <Panel title={t('recent_title')} icon={<ListChecks className="h-4 w-4 text-purple-300" aria-hidden="true" />}>
        {telemetry.recent.length === 0 ? (
          <Empty>{t('recent_empty')}</Empty>
        ) : (
          <List>
            {[...telemetry.recent].reverse().map((item, index) => (
              <Row key={`${index}-${item.neuron_id ?? 'none'}`} actions={<Pill tone={VERDICT_TONE[item.verdict]}>{t(`verdict_${item.verdict}`)}</Pill>}>
                <span className="font-mono text-xs">{item.neuron_id ?? '—'}</span>
                <p className="text-[11px] text-slate-500">
                  {t('recent_metrics', {
                    positive: percent(item.positive_similarity),
                    negative: percent(item.negative_similarity),
                    weight: percent(item.synaptic_weight),
                    ms: item.latency_ms,
                  })}
                  {item.reason ? ` · ${t(`reason_${item.reason}`)}` : ''}
                </p>
              </Row>
            ))}
          </List>
        )}
      </Panel>
    </AppFrame>
  );
};

export default View;
