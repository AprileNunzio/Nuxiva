import React from 'react';
import { ArrowRight, Link2, Lock } from 'lucide-react';
import { formatNumber, formatPair, formatPercent, formatRate } from '../../domain/format';
import { cpuRatio, ratio } from '../../domain/metrics';
import { KIND_COLORS, STALE_COLOR, withAlpha } from '../../domain/palette';
import { MeshNeuron } from '../../domain/types';
import { useMeshI18n } from '../../i18nScope';
import { TelemetryMetric } from './TelemetryMetric';

interface NeuronDetailsProps {
  readonly headingId: string;
  readonly neuron: MeshNeuron;
  readonly parentName: string;
  readonly childCount: number;
  readonly stale: boolean;
  readonly canBind: boolean;
  readonly onOpen: () => void;
  readonly onBind: () => void;
}

export const NeuronDetails: React.FC<NeuronDetailsProps> = ({
  headingId,
  neuron,
  parentName,
  childCount,
  stale,
  canBind,
  onOpen,
  onBind,
}) => {
  const { t, lang } = useMeshI18n();
  const tm = neuron.telemetry;
  const color = KIND_COLORS[neuron.kind];
  const unit = (value: string | null, suffix: string) => (value === null ? null : `${value} ${suffix}`);
  const traffic =
    tm.txKbps === null && tm.rxKbps === null
      ? null
      : `↑ ${formatRate(tm.txKbps ?? 0, lang)} · ↓ ${formatRate(tm.rxKbps ?? 0, lang)}`;

  return (
    <div className="flex flex-col gap-3">
      <header className="pr-8">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em]"
            style={{ borderColor: withAlpha(color, 0.45), color }}
          >
            {t(`kind_${neuron.kind}`)}
          </span>
          <span
            className="rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
            style={{
              borderColor: withAlpha(stale ? STALE_COLOR : '#34d399', 0.45),
              color: stale ? STALE_COLOR : '#6ee7b7',
            }}
          >
            {t(stale ? 'state_stale' : 'state_online')}
          </span>
          {neuron.isRemoteVpn && (
            <span className="flex items-center gap-1 rounded-full border border-violet-400/40 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-violet-300">
              <Lock className="h-3 w-3" aria-hidden="true" />
              {t('badge_vpn')}
            </span>
          )}
        </div>
        <h2 id={headingId} className="nm-display mt-2 break-words text-xl font-bold tracking-wide text-white">
          {neuron.name}
        </h2>
        <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs">
          <dt className="text-slate-500">{t('field_ip')}</dt>
          <dd className="truncate font-mono text-cyan-200">{neuron.ip ?? t('value_unavailable')}</dd>
          <dt className="text-slate-500">{t('field_parent')}</dt>
          <dd className="truncate text-slate-200">{parentName}</dd>
          <dt className="text-slate-500">{t('field_children')}</dt>
          <dd className="font-mono text-slate-200">{childCount}</dd>
        </dl>
      </header>

      <TelemetryMetric
        label={t('metric_cpu')}
        value={formatPercent(tm.cpuPercent, lang)}
        detail={[tm.cpuName, tm.cpuCores === null ? null : t('cpu_cores', { count: tm.cpuCores })].filter(Boolean).join(' · ') || null}
        ratio={cpuRatio(neuron)}
        color={color}
      />
      <TelemetryMetric
        label={t('metric_ram')}
        value={formatPair(tm.ramUsedGb, tm.ramTotalGb, lang, 'GB')}
        ratio={ratio(tm.ramUsedGb, tm.ramTotalGb)}
        color={color}
      />
      <TelemetryMetric
        label={t('metric_gpu')}
        value={formatPair(tm.vramUsedGb, tm.vramTotalGb, lang, 'GB')}
        detail={tm.gpuName}
        ratio={ratio(tm.vramUsedGb, tm.vramTotalGb)}
        color={color}
      />
      <div className="grid grid-cols-2 gap-2">
        <TelemetryMetric label={t('metric_power')} value={unit(formatNumber(tm.powerWatts, lang, 0), 'W')} color={color} />
        <TelemetryMetric label={t('metric_temp')} value={unit(formatNumber(tm.tempC, lang, 0), '°C')} color={color} />
        <TelemetryMetric label={t('metric_ping')} value={unit(formatNumber(tm.pingMs, lang), 'ms')} color={color} />
        <TelemetryMetric label={t('metric_os')} value={tm.os} color={color} />
      </div>
      <TelemetryMetric label={t('metric_model')} value={tm.activeModel} color={color} />
      <TelemetryMetric label={t('metric_traffic')} value={traffic} color={color} />

      <div className="mt-1 flex flex-col gap-2 sm:flex-row xl:flex-col">
        <button
          type="button"
          onClick={onOpen}
          className="flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold text-slate-950 transition hover:brightness-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-white"
          style={{ background: `linear-gradient(90deg, ${color}, #818cf8)`, boxShadow: `0 0 24px ${withAlpha(color, 0.35)}` }}
        >
          {t('action_open_neuron')}
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </button>
        {canBind && (
          <button
            type="button"
            onClick={onBind}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-900/70 px-4 py-2.5 text-sm font-semibold text-slate-200 transition hover:border-cyan-400/60 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            <Link2 className="h-4 w-4" aria-hidden="true" />
            {t('action_bind')}
          </button>
        )}
      </div>
    </div>
  );
};
