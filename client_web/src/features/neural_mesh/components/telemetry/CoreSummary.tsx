import React from 'react';
import { ArrowRight, Atom } from 'lucide-react';
import { formatNumber, formatPair, formatPercent } from '../../domain/format';
import { MeshAggregate, ratio } from '../../domain/metrics';
import { CORE_COLOR, KIND_COLORS, withAlpha } from '../../domain/palette';
import { NEURON_KINDS } from '../../domain/types';
import { useMeshI18n } from '../../i18nScope';
import { TelemetryMetric } from './TelemetryMetric';

interface CoreSummaryProps {
  readonly headingId: string;
  readonly aggregate: MeshAggregate;
  readonly onOpenCore: () => void;
}

export const CoreSummary: React.FC<CoreSummaryProps> = ({ headingId, aggregate, onOpenCore }) => {
  const { t, lang } = useMeshI18n();
  return (
    <div className="flex flex-col gap-3">
      <header className="flex items-center gap-3 pr-8">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-cyan-300/40 bg-cyan-400/10">
          <Atom className="h-5 w-5 text-cyan-200" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <h2 id={headingId} className="nm-display truncate text-lg font-bold uppercase tracking-[0.18em] text-white">
            {t('core_summary_title')}
          </h2>
          <p className="text-xs text-slate-400">{t('core_summary_subtitle')}</p>
        </div>
      </header>

      <div className="grid grid-cols-2 gap-2">
        <TelemetryMetric
          label={t('metric_neurons')}
          value={`${aggregate.online} / ${aggregate.total}`}
          ratio={ratio(aggregate.online, aggregate.total)}
          color={CORE_COLOR}
        />
        <TelemetryMetric
          label={t('metric_cpu_avg')}
          value={formatPercent(aggregate.averageCpu, lang) ?? t('value_unavailable')}
          ratio={aggregate.averageCpu === null ? null : aggregate.averageCpu / 100}
          color={CORE_COLOR}
        />
      </div>
      <TelemetryMetric
        label={t('metric_ram_total')}
        value={formatPair(aggregate.ramUsedGb, aggregate.ramTotalGb, lang, 'GB')}
        ratio={ratio(aggregate.ramUsedGb, aggregate.ramTotalGb)}
        color={CORE_COLOR}
      />
      <div className="grid grid-cols-2 gap-2">
        <TelemetryMetric label={t('metric_gpu_count')} value={formatNumber(aggregate.gpuCount, lang, 0)} color={CORE_COLOR} />
        <TelemetryMetric
          label={t('metric_power_total')}
          value={aggregate.powerWatts === null ? t('value_unavailable') : `${formatNumber(aggregate.powerWatts, lang, 0)} W`}
          color={CORE_COLOR}
        />
      </div>

      <ul className="flex flex-wrap gap-1.5" aria-label={t('legend_title')}>
        {NEURON_KINDS.map((kind) => (
          <li
            key={kind}
            className="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium"
            style={{ borderColor: withAlpha(KIND_COLORS[kind], 0.35), color: KIND_COLORS[kind] }}
          >
            <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: KIND_COLORS[kind] }} aria-hidden="true" />
            {t(`kind_${kind}`)}
            <span className="font-mono text-slate-300">{aggregate.byKind[kind]}</span>
          </li>
        ))}
      </ul>

      <button
        type="button"
        onClick={onOpenCore}
        className="mt-1 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-4 py-2.5 text-sm font-bold text-slate-950 shadow-[0_0_24px_rgba(34,211,238,0.35)] transition hover:brightness-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200"
      >
        {t('action_open_core')}
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  );
};
