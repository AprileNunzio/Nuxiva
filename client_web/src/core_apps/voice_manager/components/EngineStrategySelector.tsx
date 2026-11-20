import React from 'react';
import { Cpu, ShieldCheck, Sparkles, Zap } from 'lucide-react';
import { EngineMode } from '../types';

interface Props {
  readonly mode: EngineMode;
  readonly disabled?: boolean;
  readonly onChange: (next: EngineMode) => void;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

export const EngineStrategySelector: React.FC<Props> = ({ mode, disabled, onChange, t }) => {
  return (
    <div className="grid grid-cols-1 cq-md:grid-cols-3 gap-3">
      {/* 1. LOCALE */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange('local')}
        className={`text-left p-3.5 rounded-xl border transition relative overflow-hidden flex flex-col justify-between ${
          mode === 'local'
            ? 'border-emerald-500 bg-emerald-950/20 shadow-[0_0_15px_rgba(16,185,129,0.15)] ring-1 ring-emerald-500'
            : 'border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/60'
        }`}
      >
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="flex items-center gap-2 font-bold text-xs text-emerald-400">
              <ShieldCheck className="h-4 w-4" />
              {t('engine_local_title')}
            </span>
            {mode === 'local' && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                {t('active')}
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            {t('engine_local_desc')}
          </p>
        </div>
        <div className="mt-3 flex items-center gap-1.5 text-[10px] text-emerald-300/80 font-mono">
          <Cpu className="h-3 w-3" />
          <span>Kokoro Neurale · Piper ONNX</span>
        </div>
      </button>

      {/* 2. ELEVENLABS */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange('elevenlabs')}
        className={`text-left p-3.5 rounded-xl border transition relative overflow-hidden flex flex-col justify-between ${
          mode === 'elevenlabs'
            ? 'border-purple-500 bg-purple-950/20 shadow-[0_0_15px_rgba(168,85,247,0.15)] ring-1 ring-purple-500'
            : 'border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/60'
        }`}
      >
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="flex items-center gap-2 font-bold text-xs text-purple-400">
              <Sparkles className="h-4 w-4" />
              {t('engine_elevenlabs_title')}
            </span>
            {mode === 'elevenlabs' && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                {t('active')}
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            {t('engine_elevenlabs_desc')}
          </p>
        </div>
        <div className="mt-3 flex items-center gap-1.5 text-[10px] text-purple-300/80 font-mono">
          <span>Piano Free (10k) o Creator</span>
        </div>
      </button>

      {/* 3. IBRIDO SMART */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange('hybrid')}
        className={`text-left p-3.5 rounded-xl border transition relative overflow-hidden flex flex-col justify-between ${
          mode === 'hybrid'
            ? 'border-cyan-500 bg-cyan-950/20 shadow-[0_0_15px_rgba(6,182,212,0.15)] ring-1 ring-cyan-500'
            : 'border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/60'
        }`}
      >
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="flex items-center gap-2 font-bold text-xs text-cyan-300">
              <Zap className="h-4 w-4" />
              {t('engine_hybrid_title')}
            </span>
            {mode === 'hybrid' && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                {t('recommended')}
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            {t('engine_hybrid_desc')}
          </p>
        </div>
        <div className="mt-3 flex items-center gap-1.5 text-[10px] text-cyan-300/80 font-mono">
          <span>ElevenLabs + Fallback Locale</span>
        </div>
      </button>
    </div>
  );
};
