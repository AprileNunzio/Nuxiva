import React from 'react';
import { NavigationTab } from '../types';
import { Activity, ShieldCheck, Cpu, Terminal, Radio, Globe, Box, Gamepad2 } from 'lucide-react';
import { useI18n } from '../i18n/I18nContext';
import { SupportedLanguage } from '../i18n/translations';

interface AppNavbarProps {
  currentTab: NavigationTab;
  onTabChange: (tab: NavigationTab) => void;
  isMeshConnected: boolean;
}

export const AppNavbar: React.FC<AppNavbarProps> = ({ currentTab, onTabChange, isMeshConnected }) => {
  const { lang, setLang, t } = useI18n();

  return (
    <header className="sticky top-0 z-50 w-full backdrop-blur-md bg-[#030712]/90 border-b border-cyan-950/60 px-3 sm:px-6 py-2.5 transition-all">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-2">
        <div className="flex items-center space-x-2.5">
          <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-cyan-950/40 border border-cyan-500/40 text-cyan-400 shadow-[0_0_12px_rgba(0,240,255,0.2)]">
            <Radio className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-['Rajdhani'] font-bold text-lg sm:text-xl tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">
                NUXIVA
              </span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                v4.5.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              {t('nav_subtitle')}
            </p>
          </div>
        </div>

        <nav className="flex items-center space-x-1 overflow-x-auto scrollbar-none bg-slate-900/70 p-1 rounded-xl border border-slate-800 max-w-full">
          <button
            onClick={() => onTabChange('CORE')}
            className={`flex items-center space-x-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
              currentTab === 'CORE'
                ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            <span>{t('nav_core')}</span>
          </button>

          <button
            onClick={() => onTabChange('WORLD_3D')}
            className={`flex items-center space-x-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
              currentTab === 'WORLD_3D'
                ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Gamepad2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>{t('nav_world_3d')}</span>
          </button>

          <button
            onClick={() => onTabChange('STUDIO_3D')}
            className={`flex items-center space-x-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
              currentTab === 'STUDIO_3D'
                ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Box className="w-3.5 h-3.5 text-purple-400" />
            <span>{t('nav_studio_3d')}</span>
          </button>
          
          <button
            onClick={() => onTabChange('CONTROL_DECK')}
            className={`flex items-center space-x-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
              currentTab === 'CONTROL_DECK'
                ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Terminal className="w-3.5 h-3.5 text-blue-400" />
            <span>{t('nav_control_deck')}</span>
          </button>
        </nav>

        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-1 bg-slate-900/80 border border-slate-800 px-2 py-1 rounded-lg text-xs">
            <Globe className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value as SupportedLanguage)}
              className="bg-transparent text-slate-300 text-xs font-mono font-semibold focus:outline-none cursor-pointer"
            >
              <option value="it" className="bg-slate-900 text-slate-200">IT</option>
              <option value="en" className="bg-slate-900 text-slate-200">EN</option>
              <option value="fr" className="bg-slate-900 text-slate-200">FR</option>
            </select>
          </div>

          <div className="hidden lg:flex items-center space-x-2 bg-slate-950/60 border border-slate-800 px-2.5 py-1 rounded-lg text-xs font-mono">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-emerald-400 font-bold">Zero-Trust</span>
          </div>

          <div className="hidden xl:flex items-center space-x-2 bg-slate-950/60 border border-slate-800 px-2.5 py-1 rounded-lg text-xs font-mono">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <span className={isMeshConnected ? "text-cyan-400" : "text-amber-400"}>
              {isMeshConnected ? "MESH OK" : "SOLO"}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
