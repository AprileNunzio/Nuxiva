import React from 'react';
import { NavigationTab } from '../types';
import { Radio, Globe, ShieldCheck, Cpu, ChevronRight, Network, Layers } from 'lucide-react';
import { useI18n } from '../i18n/I18nContext';
import { SupportedLanguage } from '../i18n/translations';

interface AppNavbarProps {
  currentTab: NavigationTab;
  onTabChange: (tab: NavigationTab) => void;
  isMeshConnected: boolean;
  selectedNodeName?: string;
  selectedAppName?: string;
}

export const AppNavbar: React.FC<AppNavbarProps> = ({
  currentTab,
  onTabChange,
  isMeshConnected,
  selectedNodeName,
  selectedAppName,
}) => {
  const { lang, setLang, t } = useI18n();

  return (
    <header className="sticky top-0 z-50 w-full backdrop-blur-xl bg-[#030712]/95 border-b border-cyan-500/20 px-4 sm:px-6 py-2.5 transition-all shadow-[0_4px_30px_rgba(0,240,255,0.05)]">
      <div className="w-full max-w-7xl mx-auto flex items-center justify-between gap-4">
        {/* Brand / Logo (Always returns to Spatial Mesh Canvas) */}
        <div
          onClick={() => onTabChange('MESH_CANVAS')}
          className="flex items-center gap-3 cursor-pointer group select-none"
        >
          <div className="relative flex items-center justify-center w-9 h-9 rounded-xl bg-cyan-950/40 border border-cyan-500/50 text-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.3)] group-hover:scale-105 group-hover:border-cyan-300 transition-all">
            <Radio className="w-4 h-4 animate-pulse" />
            <div className="absolute inset-0 rounded-xl bg-cyan-400/10 blur-sm pointer-events-none" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-['Rajdhani'] font-bold text-lg sm:text-xl tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400 group-hover:from-cyan-300 group-hover:to-blue-300 transition-all">
                NUXIVA OS
              </span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
                v5.0.0 MESH
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block font-mono">
              Autonomous Mesh & Edge Platform
            </p>
          </div>
        </div>

        {/* Dynamic Holographic Breadcrumb in Center */}
        <div className="hidden md:flex items-center gap-2 px-4 py-1.5 rounded-xl bg-slate-900/70 border border-slate-800 text-xs font-mono">
          <button
            onClick={() => onTabChange('MESH_CANVAS')}
            className={`flex items-center gap-1.5 hover:text-cyan-300 transition ${
              currentTab === 'MESH_CANVAS' ? 'text-cyan-400 font-bold' : 'text-slate-400'
            }`}
          >
            <Network className="w-3.5 h-3.5 text-cyan-400" />
            <span>SPATIAL MESH</span>
          </button>

          {(currentTab === 'CORE_APPS' || currentTab === 'APP_VIEW') && (
            <>
              <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
              <button
                onClick={() => onTabChange('CORE_APPS')}
                className={`flex items-center gap-1 hover:text-cyan-300 transition ${
                  currentTab === 'CORE_APPS' ? 'text-cyan-400 font-bold' : 'text-slate-400'
                }`}
              >
                <Layers className="w-3.5 h-3.5 text-indigo-400" />
                <span>NUCLEO CENTRALE</span>
              </button>
            </>
          )}

          {currentTab === 'APP_VIEW' && selectedAppName && (
            <>
              <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
              <span className="text-cyan-300 font-bold">{selectedAppName}</span>
            </>
          )}

          {currentTab === 'NODE_CONTROL' && (
            <>
              <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
              <span className="text-emerald-400 font-bold flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                {selectedNodeName || 'NODO'}
              </span>
            </>
          )}
        </div>

        {/* Actions & Utilities */}
        <div className="flex items-center gap-3">
          {/* Quick Return to Canvas button when not on Canvas */}
          {currentTab !== 'MESH_CANVAS' && (
            <button
              onClick={() => onTabChange('MESH_CANVAS')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-xs font-mono font-bold transition shadow-[0_0_15px_rgba(0,240,255,0.15)]"
            >
              <Network className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Mappa Spaziale</span>
            </button>
          )}

          {/* Language Selector */}
          <div className="flex items-center gap-1 bg-slate-900/80 border border-slate-800 px-2.5 py-1 rounded-xl text-xs">
            <Globe className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value as SupportedLanguage)}
              className="bg-transparent text-slate-300 text-xs font-mono font-bold focus:outline-none cursor-pointer"
              aria-label="Language"
            >
              <option value="it" className="bg-slate-900 text-slate-200">IT</option>
              <option value="en" className="bg-slate-900 text-slate-200">EN</option>
              <option value="fr" className="bg-slate-900 text-slate-200">FR</option>
              <option value="es" className="bg-slate-900 text-slate-200">ES</option>
            </select>
          </div>

          {/* Zero Trust Badge */}
          <div className="hidden lg:flex items-center gap-1.5 bg-slate-950/60 border border-slate-800 px-2.5 py-1 rounded-xl text-xs font-mono">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-emerald-400 font-bold">{t('nav_zero_trust')}</span>
          </div>

          {/* Mesh Status */}
          <div className="flex items-center gap-1.5 bg-slate-950/60 border border-slate-800 px-2.5 py-1 rounded-xl text-xs font-mono">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <span className={isMeshConnected ? 'text-cyan-400 font-semibold' : 'text-amber-400 font-semibold'}>
              {isMeshConnected ? t('nav_mesh_connected') : t('nav_mesh_solo')}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
