import React from 'react';
import { Camera, Moon, Sun, Sunrise, Sunset, Cloud, Orbit } from 'lucide-react';
import type { Base, LensId, LightId, Look } from '../types';

interface LookPanelProps {
  readonly look: Look;
  readonly base: Base;
  readonly t: (key: string) => string;
  readonly onLook: (patch: Partial<Look>) => void;
  readonly onBase: (patch: Partial<Base>) => void;
}

const LIGHT_ICON: Record<LightId, React.ReactNode> = {
  golden_hour: <Sunset className="h-4 w-4" />, overcast: <Cloud className="h-4 w-4" />, blue_hour: <Sunrise className="h-4 w-4" />, noon: <Sun className="h-4 w-4" />, night: <Moon className="h-4 w-4" />,
};
const LIGHT_IDS: readonly LightId[] = ['golden_hour', 'overcast', 'blue_hour', 'noon', 'night'];
const LENS_IDS: readonly LensId[] = ['macro', 'tilt_shift', 'standard_50mm'];

const Slider: React.FC<{ label: string; value: number; min: number; max: number; step: number; onCommit: (value: number) => void }> = ({ label, value, min, max, step, onCommit }) => (
  <label className="block">
    <span className="mb-1 flex justify-between text-xs font-semibold text-slate-600"><span>{label}</span><span className="font-mono text-slate-400">{value.toFixed(step < 1 ? 2 : 0)}</span></span>
    <input type="range" min={min} max={max} step={step} defaultValue={value} key={value} onPointerUp={(e) => onCommit(Number((e.target as HTMLInputElement).value))} onKeyUp={(e) => onCommit(Number((e.target as HTMLInputElement).value))} className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-sky-600" />
  </label>
);

const Title: React.FC<{ children: React.ReactNode }> = ({ children }) => <h3 className="mb-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">{children}</h3>;

export const LookPanel: React.FC<LookPanelProps> = ({ look, base, t, onLook, onBase }) => (
  <div className="space-y-6">
    <section>
      <Title>{t('light')}</Title>
      <div className="grid grid-cols-2 gap-2">
        {LIGHT_IDS.map((id) => (
          <button key={id} type="button" onClick={() => onLook({ light: id })} className={`flex items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-xs font-semibold transition ${look.light === id ? 'border-sky-400 bg-sky-50 text-sky-800 ring-2 ring-sky-100' : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'}`}>
            {LIGHT_ICON[id]}
            {t(`light_${id}`)}
          </button>
        ))}
      </div>
    </section>
    <section>
      <Title>{t('lens')}</Title>
      <div className="space-y-2">
        {LENS_IDS.map((id) => (
          <button key={id} type="button" onClick={() => onLook({ lens: id })} className={`flex w-full items-start gap-3 rounded-xl border px-3 py-2.5 text-left transition ${look.lens === id ? 'border-sky-400 bg-sky-50 ring-2 ring-sky-100' : 'border-slate-200 bg-white hover:border-slate-300'}`}>
            <Camera className={`mt-0.5 h-4 w-4 shrink-0 ${look.lens === id ? 'text-sky-600' : 'text-slate-400'}`} />
            <span>
              <span className="block text-xs font-bold text-slate-800">{t(`lens_${id}`)}</span>
              <span className="block text-[11px] leading-snug text-slate-500">{t(`lens_${id}_hint`)}</span>
            </span>
          </button>
        ))}
      </div>
    </section>
    <section className="space-y-4">
      <Slider label={t('blur')} value={look.blur} min={0} max={1} step={0.05} onCommit={(blur) => onLook({ blur })} />
      <Slider label={t('mist')} value={look.mist} min={0} max={0.5} step={0.02} onCommit={(mist) => onLook({ mist })} />
      <Slider label={t('angle')} value={look.angle} min={10} max={85} step={1} onCommit={(angle) => onLook({ angle })} />
      <button type="button" onClick={() => onLook({ orbit: !look.orbit })} className={`flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-xs font-semibold transition ${look.orbit ? 'border-sky-400 bg-sky-50 text-sky-800' : 'border-slate-200 bg-white text-slate-600'}`}>
        <span className="flex items-center gap-2"><Orbit className="h-4 w-4" />{t('orbit')}</span>
        <span>{look.orbit ? t('on') : t('off')}</span>
      </button>
    </section>
    <section className="space-y-4">
      <Title>{t('plate')}</Title>
      <Slider label={t('plate_width')} value={base.w} min={8} max={40} step={1} onCommit={(w) => onBase({ w })} />
      <Slider label={t('plate_depth')} value={base.d} min={8} max={40} step={1} onCommit={(d) => onBase({ d })} />
    </section>
  </div>
);
