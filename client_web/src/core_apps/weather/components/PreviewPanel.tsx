import React from 'react';
import { Pill, Stat, StatRow } from '../../shared/kit';
import { Preview } from '../types';

interface Props {
  readonly preview: Preview;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

const WIND_LABEL = { kmh: 'km/h', ms: 'm/s', mph: 'mph', kn: 'kn' } as const;
const PRESSURE_LABEL = { hpa: 'hPa', inhg: 'inHg' } as const;
const degrees = (unit: 'c' | 'f') => (unit === 'f' ? '°F' : '°C');

const convert = (value: number, unit: 'c' | 'f'): number => Math.round(unit === 'f' ? (value * 9) / 5 + 32 : value);

const speed = (value: number, unit: Preview['units']['wind']): number => {
  const factor = { kmh: 1, ms: 1 / 3.6, mph: 0.621371, kn: 0.539957 }[unit];
  return Math.round(value * factor * (unit === 'ms' ? 10 : 1)) / (unit === 'ms' ? 10 : 1);
};

export const PreviewPanel: React.FC<Props> = ({ preview, t }) => {
  const unit = preview.units.temp;
  const pressure = preview.units.pressure === 'inhg' ? (preview.pressure * 0.02953).toFixed(2) : String(preview.pressure);
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-3xl font-semibold text-slate-900">
          {convert(preview.temp, unit)}
          {degrees(unit)}
        </span>
        <span className="text-sm text-slate-700">{preview.desc}</span>
        {preview.stale ? <Pill tone="amber">{t('stale')}</Pill> : null}
      </div>
      <StatRow>
        <Stat label={t('stat_feels')} value={`${convert(preview.feels, unit)}${degrees(unit)}`} tone="amber" />
        <Stat label={t('stat_humidity')} value={`${preview.humidity}%`} tone="cyan" />
        <Stat label={t('stat_wind')} value={`${speed(preview.wind, preview.units.wind)} ${WIND_LABEL[preview.units.wind]} ${preview.dirName}`} tone="emerald" />
        <Stat label={t('stat_pressure')} value={`${pressure} ${PRESSURE_LABEL[preview.units.pressure]}`} tone="purple" />
        <Stat label={t('stat_uv')} value={preview.uv} tone="rose" />
        <Stat label={t('stat_air')} value={preview.aqi === null ? '—' : preview.aqi} tone="emerald" />
      </StatRow>
      <ul className="grid gap-1.5 sm:grid-cols-2" aria-label={t('forecast')}>
        {preview.days.map((day) => (
          <li key={day.label} className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2 text-sm">
            <span className="text-slate-700">{day.label}</span>
            <span className="text-slate-900">
              {convert(day.tmin, unit)}° / {convert(day.tmax, unit)}°
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
};
