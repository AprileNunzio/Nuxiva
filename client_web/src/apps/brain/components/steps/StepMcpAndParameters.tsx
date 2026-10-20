import React from 'react';
import { BrainTargetConfig, McpToolDefinition } from '../../types';
import {
  Sliders,
  Wrench,
  Home,
  HardDrive,
  Globe,
  Terminal,
  Layers,
  Dna,
  CheckCircle2,
  Check,
  Save,
  ShieldCheck,
  Zap,
} from 'lucide-react';

interface StepMcpAndParametersProps {
  readonly target: BrainTargetConfig;
  readonly temperature: number;
  readonly onUpdateTemperature: (temp: number) => void;
  readonly mcpCatalog: readonly McpToolDefinition[];
  readonly enabledMcpTools: readonly string[];
  readonly onToggleMcpTool: (toolId: string) => void;
  readonly assignedModelName: string;
  readonly methodLabel: string;
  readonly onConfirmSave: () => void;
  readonly t: (key: string) => string;
}

export const StepMcpAndParameters: React.FC<StepMcpAndParametersProps> = ({
  target,
  temperature,
  onUpdateTemperature,
  mcpCatalog,
  enabledMcpTools,
  onToggleMcpTool,
  assignedModelName,
  methodLabel,
  onConfirmSave,
  t,
}) => {
  const renderMcpIcon = (iconName: string) => {
    switch (iconName) {
      case 'Home':
        return <Home className="w-4 h-4 text-cyan-600" />;
      case 'HardDrive':
        return <HardDrive className="w-4 h-4 text-emerald-600" />;
      case 'Globe':
        return <Globe className="w-4 h-4 text-blue-600" />;
      case 'Terminal':
        return <Terminal className="w-4 h-4 text-purple-600" />;
      case 'Layers':
        return <Layers className="w-4 h-4 text-indigo-600" />;
      case 'Dna':
        return <Dna className="w-4 h-4 text-rose-600" />;
      default:
        return <Wrench className="w-4 h-4 text-slate-600" />;
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* 1. Parametri di Inferenza - MD3 Expressive Light Slider Card */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200/80 pb-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-700 shadow-2xs">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] font-black uppercase tracking-widest text-indigo-700">Step 3A • Precisione & Stile</span>
              <h3 className="text-base font-black text-slate-950 tracking-tight">
                1. {t('inference_tuning_title')}
              </h3>
            </div>
          </div>

          <div className="flex items-center gap-2 px-3.5 py-1 rounded-xl bg-slate-50 border border-indigo-200">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Temperatura:</span>
            <span className="text-base font-black font-mono text-indigo-700">{temperature.toFixed(2)}</span>
          </div>
        </div>

        <div className="space-y-3.5">
          <div className="flex items-center justify-between text-xs sm:text-sm">
            <span className="text-slate-700 font-semibold flex items-center gap-1.5">
              <Zap className="w-4 h-4 text-amber-500" />
              <span>Modalità di Risposta:</span>
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider bg-indigo-100 border border-indigo-200 text-indigo-900">
              {temperature < 0.2
                ? t('temp_precise')
                : temperature < 0.6
                ? t('temp_balanced')
                : t('temp_creative')}
            </span>
          </div>

          <div className="relative py-1">
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={temperature}
              aria-label="Temperatura di inferenza"
              onChange={(e) => onUpdateTemperature(parseFloat(e.target.value))}
              className="w-full h-2.5 bg-slate-200 rounded-full appearance-none cursor-pointer accent-indigo-600 focus:outline-none border border-slate-300"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1 text-xs">
            <div
              onClick={() => onUpdateTemperature(0.0)}
              className={`p-3 rounded-xl border text-center cursor-pointer transition ${
                temperature <= 0.15
                  ? 'bg-indigo-50 border-2 border-indigo-400 text-indigo-950 font-bold shadow-2xs'
                  : 'bg-slate-50 border-slate-200 text-slate-600 hover:text-slate-900'
              }`}
            >
              <div className="font-black text-xs text-slate-950">0.0 - 0.15</div>
              <div className="text-[11px] mt-0.5 font-medium">Deterministico & Codice</div>
            </div>

            <div
              onClick={() => onUpdateTemperature(0.4)}
              className={`p-3 rounded-xl border text-center cursor-pointer transition ${
                temperature > 0.15 && temperature <= 0.6
                  ? 'bg-indigo-50 border-2 border-indigo-400 text-indigo-950 font-bold shadow-2xs'
                  : 'bg-slate-50 border-slate-200 text-slate-600 hover:text-slate-900'
              }`}
            >
              <div className="font-black text-xs text-slate-950">0.4 - 0.6</div>
              <div className="text-[11px] mt-0.5 font-medium">Bilanciato & Conversazione</div>
            </div>

            <div
              onClick={() => onUpdateTemperature(0.85)}
              className={`p-3 rounded-xl border text-center cursor-pointer transition ${
                temperature > 0.6
                  ? 'bg-indigo-50 border-2 border-indigo-400 text-indigo-950 font-bold shadow-2xs'
                  : 'bg-slate-50 border-slate-200 text-slate-600 hover:text-slate-900'
              }`}
            >
              <div className="font-black text-xs text-slate-950">0.85 - 1.0</div>
              <div className="text-[11px] mt-0.5 font-medium">Creativo & Brainstorming</div>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Accesso Diretto MCP da Nuxiva */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200/80 pb-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-700 shadow-2xs">
              <Wrench className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] font-black uppercase tracking-widest text-indigo-700">Step 3B • Strumenti del Mesh</span>
              <h3 className="text-base font-black text-slate-950 tracking-tight">
                2. {t('mcp_access_title')}
              </h3>
            </div>
          </div>

          <div className="px-3 py-1 rounded-full bg-emerald-100 border border-emerald-300 text-emerald-950 flex items-center gap-1.5 font-bold text-xs shadow-2xs">
            <ShieldCheck className="w-4 h-4 text-emerald-700" />
            <span>
              {enabledMcpTools.length} / {mcpCatalog.length} {t('mcp_enabled_count')}
            </span>
          </div>
        </div>

        <p className="text-xs sm:text-sm text-slate-600 leading-relaxed font-medium">
          {t('mcp_access_desc')}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 pt-1">
          {mcpCatalog.map((tool) => {
            const isEnabled = enabledMcpTools.includes(tool.id);
            return (
              <div
                key={tool.id}
                onClick={() => onToggleMcpTool(tool.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onToggleMcpTool(tool.id);
                  }
                }}
                className={`relative flex items-start justify-between p-4 rounded-xl border transition-all cursor-pointer select-none group ${
                  isEnabled
                    ? 'bg-indigo-50/70 border-2 border-indigo-400 shadow-xs ring-1 ring-indigo-200'
                    : 'bg-white border-slate-200/90 opacity-80 hover:opacity-100 hover:border-slate-300 shadow-2xs'
                }`}
              >
                <div className="flex items-start gap-3 min-w-0 pr-2.5">
                  <div className={`p-2 rounded-xl border shrink-0 mt-0.5 transition ${
                    isEnabled
                      ? 'bg-white border-indigo-300 text-indigo-700 shadow-2xs'
                      : 'bg-slate-50 border-slate-200 text-slate-600'
                  }`}>
                    {renderMcpIcon(tool.iconName)}
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs sm:text-sm font-black text-slate-950 truncate">
                      {tool.name}
                    </div>
                    <div className="text-xs text-slate-600 mt-0.5 line-clamp-2 leading-relaxed font-medium">
                      {tool.description}
                    </div>
                  </div>
                </div>

                <div
                  className={`w-5 h-5 rounded-md border flex items-center justify-center shrink-0 transition-all ${
                    isEnabled
                      ? 'bg-indigo-600 border-indigo-600 text-white font-black shadow-2xs'
                      : 'border-slate-300 bg-white text-transparent'
                  }`}
                >
                  <Check className="w-3.5 h-3.5 stroke-[3]" />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Riepilogo & Conferma Assegnazione - MD3 Expressive Light Summary Banner */}
      <div className="rounded-2xl border border-slate-200/90 bg-gradient-to-br from-slate-50 via-white to-indigo-50/30 p-5 sm:p-6 shadow-xs space-y-4">
        <div className="flex items-center gap-3 border-b border-slate-200/80 pb-3">
          <div className="p-2.5 rounded-xl bg-amber-100 text-amber-900 border border-amber-200 shadow-2xs">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] font-black uppercase tracking-widest text-amber-900">Step Finale</span>
            <h4 className="text-base font-black text-slate-950 tracking-tight">
              3. {t('summary_assignment_title')}
            </h4>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-3.5 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
            <span className="text-slate-500 block text-[10px] font-black uppercase tracking-wider">Target Nuxiva</span>
            <span className="text-slate-950 font-black text-sm truncate block mt-0.5">{target.name}</span>
          </div>

          <div className="p-3.5 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
            <span className="text-slate-500 block text-[10px] font-black uppercase tracking-wider">Metodo Calcolo</span>
            <span className="text-amber-950 font-black text-sm truncate block mt-0.5">{methodLabel}</span>
          </div>

          <div className="p-3.5 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
            <span className="text-slate-500 block text-[10px] font-black uppercase tracking-wider">LLM Assegnato</span>
            <span className="text-indigo-950 font-black text-sm truncate block mt-0.5">{assignedModelName}</span>
          </div>

          <div className="p-3.5 rounded-xl bg-white border border-slate-200/90 shadow-2xs">
            <span className="text-slate-500 block text-[10px] font-black uppercase tracking-wider">Strumenti MCP</span>
            <span className="text-emerald-950 font-black text-sm truncate block mt-0.5">{enabledMcpTools.length} attivi</span>
          </div>
        </div>

        <div className="pt-3 border-t border-slate-200/80 flex flex-wrap items-center justify-end gap-3">
          <button
            type="button"
            onClick={onConfirmSave}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-xs sm:text-sm bg-emerald-600 hover:bg-emerald-700 text-white transition shadow-sm hover:scale-102 active:scale-98 cursor-pointer"
          >
            <Save className="w-4 h-4" />
            <span>{t('save_and_assign_btn')} {target.name}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
