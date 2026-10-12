import React, { useState } from 'react';
import { 
  CloudRain, 
  Sun, 
  Snowflake, 
  CloudLightning, 
  Umbrella, 
  Send, 
  Volume2, 
  Bot 
} from 'lucide-react';
import { useI18n } from '../../shared/i18n/I18nContext';
import { WorldEnvironmentState } from '../../shared/types';
import { WeatherType } from '../spatial_assets/builders/weather_effects';

interface SpatialWorldHudProps {
  worldState: WorldEnvironmentState;
  speechText: string;
  isProcessing: boolean;
  onWeatherChange: (weather: WeatherType) => void;
  onSendCommand: (command: string) => void;
}

export const SpatialWorldHud: React.FC<SpatialWorldHudProps> = ({
  worldState,
  speechText,
  isProcessing,
  onWeatherChange,
  onSendCommand
}) => {
  const { t } = useI18n();
  const [inputText, setInputText] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    onSendCommand(inputText);
    setInputText('');
  };

  return (
    <>
      {/* Top Header & Weather Bar */}
      <div className="absolute top-2.5 sm:top-4 8k:top-8 left-2.5 sm:left-4 8k:left-8 right-2.5 sm:right-4 8k:right-8 flex flex-wrap items-center justify-between gap-2 pointer-events-none z-20">
        <div className="backdrop-blur-md bg-slate-900/85 border border-slate-800 p-2 sm:p-3 8k:p-6 rounded-2xl 8k:rounded-3xl pointer-events-auto flex items-center space-x-2.5 sm:space-x-3 8k:space-x-5 shadow-2xl">
          <div className="w-8 h-8 sm:w-10 sm:h-10 8k:w-16 8k:h-16 rounded-xl 8k:rounded-2xl bg-cyan-950/60 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
            <Bot className="w-4 h-4 sm:w-5 sm:h-5 8k:w-8 8k:h-8 animate-pulse" />
          </div>
          <div>
            <h1 className="text-xs sm:text-sm 8k:text-2xl font-bold text-slate-100 flex items-center gap-1.5 sm:gap-2">
              {t('world_title')}
              <span className="text-[9px] sm:text-[10px] 8k:text-sm uppercase font-mono px-1.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                LIVING 3D
              </span>
            </h1>
            <p className="text-[10px] sm:text-xs 8k:text-lg text-slate-400 hidden sm:block">
              {t('world_subtitle')}
            </p>
          </div>
        </div>

        {/* Weather switcher */}
        <div className="backdrop-blur-md bg-slate-900/85 border border-slate-800 p-1 8k:p-2 rounded-2xl 8k:rounded-3xl pointer-events-auto flex items-center space-x-1 8k:space-x-2 shadow-2xl">
          <button
            onClick={() => onWeatherChange('CLEAR')}
            title={t('world_weather_clear')}
            aria-label={t('world_weather_clear')}
            className={`p-2 8k:p-4 rounded-xl 8k:rounded-2xl transition-all ${worldState.weather === 'CLEAR' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}
          >
            <Sun className="w-4 h-4 8k:w-7 8k:h-7" />
          </button>
          <button
            onClick={() => onWeatherChange('RAIN')}
            title={t('world_weather_rain')}
            aria-label={t('world_weather_rain')}
            className={`p-2 8k:p-4 rounded-xl 8k:rounded-2xl transition-all ${worldState.weather === 'RAIN' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}
          >
            <CloudRain className="w-4 h-4 8k:w-7 8k:h-7" />
          </button>
          <button
            onClick={() => onWeatherChange('SNOW')}
            title={t('world_weather_snow')}
            aria-label={t('world_weather_snow')}
            className={`p-2 8k:p-4 rounded-xl 8k:rounded-2xl transition-all ${worldState.weather === 'SNOW' ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40 shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}
          >
            <Snowflake className="w-4 h-4 8k:w-7 8k:h-7" />
          </button>
          <button
            onClick={() => onWeatherChange('THUNDERSTORM')}
            title={t('world_weather_thunder')}
            aria-label={t('world_weather_thunder')}
            className={`p-2 8k:p-4 rounded-xl 8k:rounded-2xl transition-all ${worldState.weather === 'THUNDERSTORM' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}
          >
            <CloudLightning className="w-4 h-4 8k:w-7 8k:h-7" />
          </button>
        </div>
      </div>

      {/* Floating Avatar Speech bubble */}
      <div className="absolute top-16 sm:top-20 8k:top-28 left-1/2 -translate-x-1/2 max-w-lg 4xl:max-w-xl 8k:max-w-4xl w-[94%] sm:w-full px-2 pointer-events-none z-20">
        <div className="backdrop-blur-xl bg-slate-900/90 border border-cyan-500/30 rounded-2xl 8k:rounded-3xl p-3 sm:p-4 8k:p-7 shadow-[0_0_25px_rgba(0,240,255,0.15)] flex items-start space-x-2.5 sm:space-x-3 8k:space-x-5 pointer-events-auto">
          <div className="p-1.5 sm:p-2 8k:p-3 rounded-xl 8k:rounded-2xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 mt-0.5 shrink-0">
            <Volume2 className="w-4 h-4 8k:w-7 8k:h-7 animate-pulse" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1 gap-1">
              <span className="text-[11px] sm:text-xs 8k:text-base font-bold text-cyan-300 tracking-wide font-mono">
                {t('brand_name')}
              </span>
              {worldState.equippedItem && (
                <span className="text-[9px] sm:text-[10px] 8k:text-sm font-mono px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1">
                  <Umbrella className="w-3 h-3 8k:w-5 8k:h-5" /> {t('world_equipped_umbrella')}
                </span>
              )}
            </div>
            <p className="text-[11px] sm:text-xs md:text-sm 8k:text-xl text-slate-200 leading-relaxed font-sans">
              {speechText}
            </p>
          </div>
        </div>
      </div>

      {/* Command prompt form */}
      <div className="absolute bottom-4 sm:bottom-6 8k:bottom-12 left-1/2 -translate-x-1/2 max-w-2xl 4xl:max-w-3xl 8k:max-w-5xl w-[94%] sm:w-full px-2 pointer-events-auto z-20">
        <form 
          onSubmit={handleSubmit}
          className="backdrop-blur-2xl bg-slate-900/90 border border-slate-800 rounded-2xl 8k:rounded-3xl p-1.5 sm:p-2 8k:p-4 flex items-center space-x-2 8k:space-x-4 shadow-2xl focus-within:border-cyan-500/50 transition-all"
        >
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={t('world_ask_placeholder')}
            className="flex-1 bg-transparent px-3 sm:px-4 8k:px-6 py-1.5 sm:py-2 8k:py-4 text-xs sm:text-sm 8k:text-xl text-slate-100 placeholder-slate-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={!inputText.trim() || isProcessing}
            className="px-3.5 sm:px-5 8k:px-8 py-2 sm:py-2.5 8k:py-4 rounded-xl 8k:rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-500 text-slate-950 font-bold text-xs sm:text-sm 8k:text-xl flex items-center space-x-1.5 8k:space-x-3 hover:opacity-90 disabled:opacity-40 transition-all shadow-[0_0_15px_rgba(0,240,255,0.3)]"
          >
            <span>{t('send')}</span>
            <Send className="w-3.5 h-3.5 8k:w-6 8k:h-6" />
          </button>
        </form>
      </div>
    </>
  );
};
