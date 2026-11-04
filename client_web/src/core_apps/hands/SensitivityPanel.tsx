import React from 'react';
import { Panel, Toggle, inputClass } from '../shared/kit';
import { GestureProfile, Handedness } from './types';

type Translate = (key: string, params?: Record<string, string | number>) => string;

interface Slider {
  readonly key: string;
  readonly min: number;
  readonly max: number;
  readonly step: number;
  readonly read: (p: GestureProfile) => number;
  readonly write: (p: GestureProfile, v: number) => GestureProfile;
}

const SLIDERS: readonly Slider[] = [
  { key: 'pinch_on', min: 0.1, max: 0.6, step: 0.01, read: (p) => p.pinch_on, write: (p, v) => ({ ...p, pinch_on: v, pinch_off: Math.max(p.pinch_off, v) }) },
  { key: 'pinch_off', min: 0.2, max: 1, step: 0.01, read: (p) => p.pinch_off, write: (p, v) => ({ ...p, pinch_off: Math.max(v, p.pinch_on) }) },
  { key: 'follow', min: 0.1, max: 1, step: 0.05, read: (p) => p.follow, write: (p, v) => ({ ...p, follow: v }) },
  { key: 'smoothing', min: 0.1, max: 5, step: 0.1, read: (p) => p.smoothing.min_cutoff, write: (p, v) => ({ ...p, smoothing: { ...p.smoothing, min_cutoff: v } }) },
  { key: 'swipe_distance', min: 0.05, max: 0.6, step: 0.01, read: (p) => p.motion.swipe_distance, write: (p, v) => ({ ...p, motion: { ...p.motion, swipe_distance: v } }) },
  { key: 'hold_ms', min: 200, max: 3000, step: 50, read: (p) => p.motion.hold_ms, write: (p, v) => ({ ...p, motion: { ...p.motion, hold_ms: Math.round(v) } }) },
  { key: 'cooldown_ms', min: 100, max: 3000, step: 50, read: (p) => p.motion.cooldown_ms, write: (p, v) => ({ ...p, motion: { ...p.motion, cooldown_ms: Math.round(v) } }) },
  { key: 'zone_margin', min: 0, max: 0.4, step: 0.01, read: (p) => p.zone.x0, write: (p, v) => ({ ...p, zone: { ...p.zone, x0: v, x1: Math.round((1 - v) * 100) / 100 } }) },
];

interface SensitivityPanelProps {
  readonly t: Translate;
  readonly profile: GestureProfile;
  readonly onChange: (next: GestureProfile) => void;
}

export const SensitivityPanel: React.FC<SensitivityPanelProps> = ({ t, profile, onChange }) => (
  <Panel title={t('sensitivity_title')}>
    <div className="grid gap-4 sm:grid-cols-2">
      {SLIDERS.map((slider) => {
        const value = slider.read(profile);
        return (
          <label key={slider.key} className="flex flex-col gap-1 text-xs font-semibold text-slate-600">
            <span className="flex items-center justify-between gap-2">
              {t(`tune_${slider.key}`)}
              <span className="font-mono text-slate-800">{Number.isInteger(value) ? value : value.toFixed(2)}</span>
            </span>
            <input
              type="range"
              min={slider.min}
              max={slider.max}
              step={slider.step}
              value={value}
              onChange={(e) => onChange(slider.write(profile, Number(e.target.value)))}
              className="w-full accent-cyan-600"
            />
            <span className="font-normal text-slate-500">{t(`tune_${slider.key}_hint`)}</span>
          </label>
        );
      })}
      <label className="flex flex-col gap-1 text-xs font-semibold text-slate-600">
        {t('tune_dominant')}
        <select className={inputClass} value={profile.dominant} onChange={(e) => onChange({ ...profile, dominant: e.target.value as Handedness })}>
          <option value="right">{t('hand_right')}</option>
          <option value="left">{t('hand_left')}</option>
        </select>
      </label>
      <div className="flex flex-col gap-3 text-xs font-semibold text-slate-600">
        <span className="flex items-center gap-2">
          <Toggle checked={profile.pointer} onChange={(value) => onChange({ ...profile, pointer: value })} label={t('tune_pointer')} />
          {t('tune_pointer')}
        </span>
        <span className="flex items-center gap-2">
          <Toggle checked={profile.mirror} onChange={(value) => onChange({ ...profile, mirror: value })} label={t('tune_mirror')} />
          {t('tune_mirror')}
        </span>
      </div>
    </div>
  </Panel>
);
