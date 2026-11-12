import React from 'react';

interface TelemetryMetricProps {
  readonly label: string;
  readonly value: string | null;
  readonly detail?: string | null;
  readonly ratio?: number | null;
  readonly color: string;
}

export const TelemetryMetric: React.FC<TelemetryMetricProps> = ({ label, value, detail, ratio, color }) => {
  if (value === null) {
    return null;
  }
  const percent = ratio === null || ratio === undefined ? null : Math.round(ratio * 100);
  return (
    <div className="rounded-xl border border-slate-800/80 bg-slate-950/50 px-3 py-2">
      <p className="truncate text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">{label}</p>
      <p className="mt-0.5 truncate font-mono text-sm font-semibold text-slate-50" title={value}>
        {value}
      </p>
      {detail && <p className="mt-0.5 truncate text-[11px] text-slate-500">{detail}</p>}
      {percent !== null && (
        <div
          className="mt-1.5 h-1 overflow-hidden rounded-full bg-slate-800"
          role="meter"
          aria-label={label}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
        >
          <div
            className="h-full rounded-full transition-[width] duration-500"
            style={{ width: `${percent}%`, background: `linear-gradient(90deg, ${color}, #818cf8)` }}
          />
        </div>
      )}
    </div>
  );
};
