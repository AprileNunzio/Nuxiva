import React from 'react';
import { Activity, Clock, MemoryStick, Thermometer } from 'lucide-react';
import { MeshNeuron, formatNumber, formatPair, formatPercent } from '../../../features/neural_mesh';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { CONSOLE_SCOPE } from '../scope';

interface NodeLiveStripProps {
  readonly neuron: MeshNeuron | null;
}

export const NodeLiveStrip: React.FC<NodeLiveStripProps> = ({ neuron }) => {
  const { t, lang } = useScopedI18n(CONSOLE_SCOPE);
  const tm = neuron?.telemetry;
  const na = t('value_unavailable');
  const uptime = tm?.uptimeSeconds ?? null;
  const cells = [
    { key: 'cpu', icon: Activity, value: formatPercent(tm?.cpuPercent ?? null, lang), detail: tm?.cpuName ?? null },
    { key: 'ram', icon: MemoryStick, value: formatPair(tm?.ramUsedGb ?? null, tm?.ramTotalGb ?? null, lang, 'GB'), detail: null },
    {
      key: 'temp',
      icon: Thermometer,
      value: tm?.tempC == null ? null : `${formatNumber(tm.tempC, lang, 0)} °C`,
      detail: null,
    },
    {
      key: 'uptime',
      icon: Clock,
      value:
        uptime === null ? null : t('uptime_value', { days: Math.floor(uptime / 86400), hours: Math.floor((uptime % 86400) / 3600) }),
      detail: tm?.os ?? null,
    },
  ];

  return (
    <dl className="grid grid-cols-2 gap-2 lg:grid-cols-4">
      {cells.map(({ key, icon: Icon, value, detail }) => (
        <div key={key} className="rounded-xl border border-slate-800/80 bg-slate-950/50 px-3 py-2.5">
          <dt className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
            <Icon className="h-3.5 w-3.5 text-cyan-300" aria-hidden="true" />
            {t(`live_${key}`)}
          </dt>
          <dd className="mt-1 truncate font-mono text-base font-semibold text-white">{value ?? na}</dd>
          {detail && <dd className="truncate text-[11px] text-slate-500">{detail}</dd>}
        </div>
      ))}
    </dl>
  );
};
