import React from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { Field } from '../shared/kit';
import { StudioEQ, StudioFX } from './studioApi';
import { Sliders, Volume2, Sparkles, Wand2, RotateCcw } from 'lucide-react';

interface Props {
  eq: StudioEQ;
  fx: StudioFX;
  onChangeEQ: (eq: StudioEQ) => void;
  onChangeFX: (fx: StudioFX) => void;
  onApplyPreset: (presetKey: string) => void;
  onReset: () => void;
  onPreview: () => void;
  onSave?: () => void;
  busy: boolean;
  selectedVoiceName?: string;
}

export const EqualizerController: React.FC<Props> = ({
  eq,
  fx,
  onChangeEQ,
  onChangeFX,
  onApplyPreset,
  onReset,
  onPreview,
  onSave,
  busy,
  selectedVoiceName,
}) => {
  const { t } = useScopedI18n('core_apps/voice_studio');

  const updateBand = (band: keyof StudioEQ, val: number) => {
    onChangeEQ({ ...eq, [band]: val });
  };

  const updateFX = (param: keyof StudioFX, val: number) => {
    onChangeFX({ ...fx, [param]: val });
  };

  const bands: { key: keyof StudioEQ; label: string; freq: string; min: number; max: number }[] = [
    { key: 'bass', label: t('eq_bass'), freq: '80 Hz', min: -12, max: 12 },
    { key: 'low_mid', label: t('eq_low_mid'), freq: '250 Hz', min: -12, max: 12 },
    { key: 'mid', label: t('eq_mid'), freq: '1.0 kHz', min: -12, max: 12 },
    { key: 'presence', label: t('eq_presence'), freq: '3.5 kHz', min: -12, max: 12 },
    { key: 'air', label: t('eq_air'), freq: '8.0 kHz', min: -12, max: 12 },
  ];

  const presets = [
    { id: 'broadcast', name: t('preset_broadcast') },
    { id: 'warm', name: t('preset_warm') },
    { id: 'crystal', name: t('preset_crystal') },
    { id: 'vintage', name: t('preset_vintage') },
    { id: 'natural', name: t('preset_natural') },
  ];

  return (
    <div className="space-y-6">
      {/* Header e Selezione Preset con Alto Contrasto */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-cyan-300 pb-4">
        <div>
          <h4 className="flex items-center gap-2 text-base font-bold text-slate-950">
            <Sliders className="h-5 w-5 text-cyan-600" aria-hidden="true" />
            {t('equalizer_title')}
            {selectedVoiceName && <span className="text-xs font-medium text-cyan-800">({selectedVoiceName})</span>}
          </h4>
          <p className="text-xs text-slate-700">{t('equalizer_subtitle')}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-slate-800">{t('presets')}:</span>
          {presets.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => onApplyPreset(p.id)}
              className="rounded-xl border border-slate-300 bg-slate-100 px-3.5 py-1.5 text-xs font-bold text-white transition hover:border-cyan-400 hover:bg-cyan-500 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 shadow-sm"
            >
              {p.name}
            </button>
          ))}
          <button
            type="button"
            onClick={onReset}
            className="flex items-center gap-1.5 rounded-xl border border-slate-300 bg-slate-100 px-3.5 py-1.5 text-xs font-bold text-slate-950 transition hover:bg-slate-200 hover:border-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 shadow-sm"
            title={t('reset')}
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            {t('reset')}
          </button>
        </div>
      </div>

      {/* Visualizzatore e Cursori Equalizzatore a 5 Bande */}
      <div className="rounded-2xl border border-slate-300 bg-white p-5 shadow-lg">
        <div className="mb-4 flex items-center justify-between text-xs">
          <span className="font-bold text-cyan-700">{t('graphic_eq')} (5 Bande)</span>
          <span className="text-slate-700">Regolazione guadagno da -12 dB a +12 dB</span>
        </div>

        <div className="grid grid-cols-5 gap-3 pt-2 text-center" role="group" aria-label="Equalizzatore a 5 bande">
          {bands.map((b) => {
            const val = eq[b.key] ?? 0;
            return (
              <div key={b.key} className="flex flex-col items-center">
                <span className="text-xs font-bold text-slate-950">
                  {val > 0 ? `+${val.toFixed(1)}` : val.toFixed(1)} dB
                </span>
                <div className="relative my-3 flex h-40 w-10 items-center justify-center rounded-xl border border-slate-300 bg-white py-3">
                  {/* Linea zero centrale */}
                  <div className="absolute top-1/2 h-0.5 w-full -translate-y-1/2 bg-slate-600" aria-hidden="true" />
                  <input
                    type="range"
                    min={b.min}
                    max={b.max}
                    step={0.5}
                    value={val}
                    aria-label={`${b.label} (${b.freq})`}
                    aria-valuenow={val}
                    aria-valuemin={b.min}
                    aria-valuemax={b.max}
                    onChange={(e) => updateBand(b.key, parseFloat(e.target.value))}
                    className="h-32 w-5 cursor-pointer appearance-none bg-transparent accent-cyan-400 [writing-mode:vertical-lr] [direction:rtl] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                    style={{ WebkitAppearance: 'slider-vertical' }}
                  />
                </div>
                <span className="text-xs font-bold text-slate-900">{b.label}</span>
                <span className="text-[11px] font-medium text-cyan-600">{b.freq}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Sezione Voice Controller Dinamico */}
      <div className="rounded-2xl border border-slate-300 bg-white p-5 shadow-lg">
        <h5 className="mb-4 flex items-center gap-2 text-sm font-bold text-cyan-700">
          <Wand2 className="h-4 w-4 text-cyan-600" aria-hidden="true" />
          {t('voice_controller_title')}
        </h5>

        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {/* Pitch */}
          <Field label={`${t('pitch')}: ${fx.pitch > 0 ? `+${fx.pitch.toFixed(1)}` : fx.pitch.toFixed(1)} st`}>
            <input
              type="range"
              min={-8}
              max={8}
              step={0.5}
              value={fx.pitch}
              aria-label={t('pitch')}
              aria-valuenow={fx.pitch}
              onChange={(e) => updateFX('pitch', parseFloat(e.target.value))}
              className="w-full cursor-pointer accent-cyan-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            />
            <div className="flex justify-between text-xs font-medium text-slate-700">
              <span>{t('pitch_deep')} (-8)</span>
              <span>{t('normal')} (0)</span>
              <span>{t('pitch_high')} (+8)</span>
            </div>
          </Field>

          {/* Velocità */}
          <Field label={`${t('speed')}: ${fx.speed.toFixed(2)}x`}>
            <input
              type="range"
              min={0.6}
              max={1.6}
              step={0.05}
              value={fx.speed}
              aria-label={t('speed')}
              aria-valuenow={fx.speed}
              onChange={(e) => updateFX('speed', parseFloat(e.target.value))}
              className="w-full cursor-pointer accent-cyan-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            />
            <div className="flex justify-between text-xs font-medium text-slate-700">
              <span>0.6x</span>
              <span>1.0x</span>
              <span>1.6x</span>
            </div>
          </Field>

          {/* De-Esser */}
          <Field label={`${t('deesser')}: ${fx.deesser.toFixed(0)}%`}>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={fx.deesser}
              aria-label={t('deesser')}
              aria-valuenow={fx.deesser}
              onChange={(e) => updateFX('deesser', parseFloat(e.target.value))}
              className="w-full cursor-pointer accent-cyan-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            />
            <div className="flex justify-between text-xs font-medium text-slate-700">
              <span>{t('off')}</span>
              <span>{t('attenuate_sibilants')}</span>
            </div>
          </Field>

          {/* Riverbero */}
          <Field label={`${t('reverb')}: ${fx.reverb.toFixed(0)}%`}>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={fx.reverb}
              aria-label={t('reverb')}
              aria-valuenow={fx.reverb}
              onChange={(e) => updateFX('reverb', parseFloat(e.target.value))}
              className="w-full cursor-pointer accent-cyan-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            />
            <div className="flex justify-between text-xs font-medium text-slate-700">
              <span>{t('dry')}</span>
              <span>{t('room_ambience')}</span>
            </div>
          </Field>

          {/* Compressore Dinamico / Studio Limiter */}
          <Field label={`${t('compressor')}: ${fx.compressor.toFixed(0)}%`}>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={fx.compressor}
              aria-label={t('compressor')}
              aria-valuenow={fx.compressor}
              onChange={(e) => updateFX('compressor', parseFloat(e.target.value))}
              className="w-full cursor-pointer accent-cyan-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            />
            <div className="flex justify-between text-xs font-medium text-slate-700">
              <span>{t('dynamic')}</span>
              <span>{t('punch_broadcast')}</span>
            </div>
          </Field>
        </div>
      </div>

      {/* Azioni Anteprima e Salva */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <div className="flex items-center gap-2 text-xs text-slate-700">
          <Sparkles className="h-4 w-4 text-cyan-600" aria-hidden="true" />
          <span>{t('realtime_fx_hint')}</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={onPreview}
            className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 px-5 py-2.5 text-xs font-bold text-slate-950 shadow-md shadow-cyan-500/20 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 disabled:opacity-50"
          >
            <Volume2 className="h-4 w-4" aria-hidden="true" />
            {t('preview_with_fx')}
          </button>
          {onSave && (
            <button
              type="button"
              disabled={busy}
              onClick={onSave}
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 px-5 py-2.5 text-xs font-bold text-slate-950 shadow-md shadow-emerald-500/20 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300 disabled:opacity-50"
            >
              {t('save_to_voice')}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
