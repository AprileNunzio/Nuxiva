import React from 'react';
import { LevelZone } from '../data/micTestApi';

export const METER_FLOOR_DB = -60;
const QUIET_DB = -38.4;
const LOUD_DB = -12;
const CLIP_DB = -1;

export const ZONE_TEXT: Readonly<Record<LevelZone, string>> = {
  silent: 'text-slate-400',
  quiet: 'text-amber-300',
  good: 'text-emerald-300',
  loud: 'text-orange-300',
  clip: 'text-rose-300',
};

export function meterPercent(db: number): number {
  return Math.min(100, Math.max(0, ((db - METER_FLOOR_DB) / -METER_FLOOR_DB) * 100));
}

const BANDS = [
  { from: METER_FLOOR_DB, to: QUIET_DB, color: 'bg-amber-400/25' },
  { from: QUIET_DB, to: LOUD_DB, color: 'bg-emerald-400/25' },
  { from: LOUD_DB, to: CLIP_DB, color: 'bg-orange-400/25' },
  { from: CLIP_DB, to: 0, color: 'bg-rose-500/40' },
] as const;

function fillColor(db: number): string {
  if (db >= CLIP_DB) {
    return 'bg-rose-500';
  }
  if (db >= LOUD_DB) {
    return 'bg-orange-400';
  }
  return db >= QUIET_DB ? 'bg-emerald-400' : 'bg-amber-400';
}

interface LevelMeterProps {
  readonly rmsDb: number;
  readonly peakHoldDb: number;
  readonly label: string;
  readonly valueText: string;
}

export const LevelMeter: React.FC<LevelMeterProps> = ({ rmsDb, peakHoldDb, label, valueText }) => (
  <div
    role="meter"
    aria-label={label}
    aria-valuemin={METER_FLOOR_DB}
    aria-valuemax={0}
    aria-valuenow={Math.round(Math.max(METER_FLOOR_DB, rmsDb))}
    aria-valuetext={valueText}
    className="relative h-6 w-full overflow-hidden rounded-lg border border-slate-700 bg-slate-950"
  >
    {BANDS.map((band) => (
      <span
        key={band.from}
        aria-hidden="true"
        className={`absolute inset-y-0 ${band.color}`}
        style={{ left: `${meterPercent(band.from)}%`, width: `${meterPercent(band.to) - meterPercent(band.from)}%` }}
      />
    ))}
    <span
      aria-hidden="true"
      className={`absolute inset-y-1 left-0 rounded-r transition-[width] duration-75 ${fillColor(rmsDb)}`}
      style={{ width: `${meterPercent(rmsDb)}%` }}
    />
    <span aria-hidden="true" className="absolute inset-y-0 w-0.5 bg-white/90" style={{ left: `calc(${meterPercent(peakHoldDb)}% - 1px)` }} />
  </div>
);
