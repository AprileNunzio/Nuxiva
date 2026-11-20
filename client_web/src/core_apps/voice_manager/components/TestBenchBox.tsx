import React, { useState } from 'react';
import { Radio, Volume2, Wand2 } from 'lucide-react';
import { Btn, inputClass } from '../../shared/kit';
import { EngineSettings } from '../types';

interface Props {
  readonly settings: EngineSettings;
  readonly isSpeaking: boolean;
  readonly busy: boolean;
  readonly onTestSpeech: (text: string) => void;
  readonly onSpeakToRoom: (text: string) => void;
  readonly onUpdateTuning: (tuning: Partial<EngineSettings>) => void;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

const PRESET_PHRASES = [
  { label: '☀️ Saluto', text: 'Buongiorno Comandante, tutti i sottosistemi di Nuxiva sono operativi e pronti.' },
  { label: '💡 Domotica', text: 'Ho regolato la climatizzazione a ventuno gradi e spento le luci del laboratorio.' },
  { label: '⚠️ Allerta', text: 'Attenzione: rilevato movimento non autorizzato nel perimetro esterno.' },
  { label: '🎭 Assistente', text: 'Sono a tua completa disposizione per qualsiasi operazione o analisi.' },
];

export const TestBenchBox: React.FC<Props> = ({
  settings,
  isSpeaking,
  busy,
  onTestSpeech,
  onSpeakToRoom,
  onUpdateTuning,
  t,
}) => {
  const [testText, setTestText] = useState(PRESET_PHRASES[0].text);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-3">
      {/* HEADER WITH WAVEFORM */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wand2 className="h-4 w-4 text-cyan-400" />
          <h4 className="font-bold text-xs text-slate-200">{t('test_bench_title')}</h4>
        </div>

        {/* Dynamic Waveform Visualizer */}
        <div className="flex items-end gap-1 h-5 px-2 py-0.5 rounded bg-slate-950/80 border border-slate-800">
          {[1, 2, 3, 4, 5, 6, 7].map((i) => (
            <div
              key={i}
              className={`w-1 rounded-full transition-all duration-75 ${
                isSpeaking ? 'bg-cyan-400 animate-pulse' : 'bg-slate-700'
              }`}
              style={{
                height: isSpeaking ? `${Math.floor(Math.random() * 14) + 4}px` : '4px',
              }}
            />
          ))}
        </div>
      </div>

      {/* AUDIO TUNING CONTROLS (Speed, Pitch, Volume) */}
      <div className="grid grid-cols-3 gap-3 pt-1">
        <div>
          <div className="flex justify-between text-[10px] text-slate-400 mb-1">
            <span>{t('speed')}</span>
            <span className="font-mono text-cyan-300">{settings.speed}x</span>
          </div>
          <input
            type="range"
            min="0.6"
            max="1.6"
            step="0.05"
            value={settings.speed}
            onChange={(e) => onUpdateTuning({ speed: parseFloat(e.target.value) })}
            className="w-full accent-cyan-400 cursor-pointer"
          />
        </div>

        <div>
          <div className="flex justify-between text-[10px] text-slate-400 mb-1">
            <span>{t('pitch')}</span>
            <span className="font-mono text-cyan-300">
              {settings.pitch > 0 ? `+${settings.pitch}` : settings.pitch}
            </span>
          </div>
          <input
            type="range"
            min="-5"
            max="5"
            step="0.5"
            value={settings.pitch}
            onChange={(e) => onUpdateTuning({ pitch: parseFloat(e.target.value) })}
            className="w-full accent-cyan-400 cursor-pointer"
          />
        </div>

        <div>
          <div className="flex justify-between text-[10px] text-slate-400 mb-1">
            <span>{t('volume')}</span>
            <span className="font-mono text-cyan-300">{Math.round(settings.volume * 100)}%</span>
          </div>
          <input
            type="range"
            min="0.4"
            max="2.0"
            step="0.1"
            value={settings.volume}
            onChange={(e) => onUpdateTuning({ volume: parseFloat(e.target.value) })}
            className="w-full accent-cyan-400 cursor-pointer"
          />
        </div>
      </div>

      {/* PRESET CHIPS */}
      <div className="flex flex-wrap items-center gap-1.5 pt-1">
        <span className="text-[10px] text-slate-400">{t('quick_phrases')}:</span>
        {PRESET_PHRASES.map((preset) => (
          <button
            key={preset.label}
            type="button"
            onClick={() => setTestText(preset.text)}
            className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* INPUT & ACTION BUTTONS */}
      <div className="flex flex-col sm:flex-row gap-2">
        <input
          type="text"
          value={testText}
          onChange={(e) => setTestText(e.target.value)}
          placeholder={t('test_text_placeholder')}
          className={`${inputClass} flex-1 text-xs`}
        />
        <div className="flex gap-2">
          <Btn tone="cyan" busy={isSpeaking} onClick={() => onTestSpeech(testText)}>
            <Volume2 className="h-3.5 w-3.5 mr-1" />
            {t('play_in_browser')}
          </Btn>
          <Btn tone="slate" busy={busy} onClick={() => onSpeakToRoom(testText)} title={t('speak_to_room_hint')}>
            <Radio className="h-3.5 w-3.5 mr-1 text-amber-400" />
            {t('speak_to_room')}
          </Btn>
        </div>
      </div>
    </div>
  );
};
