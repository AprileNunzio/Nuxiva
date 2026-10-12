import React, { useState } from 'react';
import { NavigationTab } from '../types';
import { Activity, ShieldCheck, Cpu, Terminal, Radio, Globe, Box, Gamepad2, Menu, X } from 'lucide-react';
import { useI18n } from '../i18n/I18nContext';
import { SupportedLanguage } from '../i18n/translations';

interface AppNavbarProps {
  currentTab: NavigationTab;
  onTabChange: (tab: NavigationTab) => void;
  isMeshConnected: boolean;
}

export const AppNavbar: React.FC<AppNavbarProps> = ({ currentTab, onTabChange, isMeshConnected }) => {
  const { lang, setLang, t } = useI18n();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems: { tab: NavigationTab; labelKey: 'nav_core' | 'nav_world_3d' | 'nav_studio_3d' | 'nav_control_deck'; icon: React.ReactNode }[] = [
    { tab: 'CORE', labelKey: 'nav_core', icon: <Activity className="w-4 h-4 8k:w-7 8k:h-7 text-cyan-400" /> },
    { tab: 'WORLD_3D', labelKey: 'nav_world_3d', icon: <Gamepad2 className="w-4 h-4 8k:w-7 8k:h-7 text-emerald-400" /> },
    { tab: 'STUDIO_3D', labelKey: 'nav_studio_3d', icon: <Box className="w-4 h-4 8k:w-7 8k:h-7 text-purple-400" /> },
    { tab: 'CONTROL_DECK', labelKey: 'nav_control_deck', icon: <Terminal className="w-4 h-4 8k:w-7 8k:h-7 text-blue-400" /> },
  ];

  const handleSelectTab = (tab: NavigationTab) => {
    onTabChange(tab);
    setMobileMenuOpen(false);
  };

  return (
    <header className="sticky top-0 z-50 w-full backdrop-blur-xl bg-[#030712]/90 border-b border-cyan-950/60 px-3 sm:px-6 3xl:px-10 8k:px-16 py-2 sm:py-3 transition-all">
      <div className="w-full max-w-7xl 3xl:max-w-[1800px] 4xl:max-w-[2400px] 5xl:max-w-[3600px] 8k:max-w-[7200px] mx-auto flex items-center justify-between gap-3">
        {/* Brand */}
        <div className="flex items-center space-x-2.5 8k:space-x-5">
          <div className="flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 8k:w-16 8k:h-16 rounded-xl 8k:rounded-2xl bg-cyan-950/40 border border-cyan-500/40 text-cyan-400 shadow-[0_0_12px_rgba(0,240,255,0.2)]">
            <Radio className="w-4 h-4 sm:w-5 sm:h-5 8k:w-8 8k:h-8 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-['Rajdhani'] font-bold text-lg sm:text-xl 8k:text-3xl tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">
                {t('brand_name')}
              </span>
              <span className="text-[10px] 8k:text-sm uppercase font-mono px-1.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                {t('app_version')}
              </span>
            </div>
            <p className="text-[11px] 8k:text-base text-slate-400 hidden md:block">
              {t('nav_subtitle')}
            </p>
          </div>
        </div>

        {/* Desktop & 8K Navigation */}
        <nav className="hidden md:flex items-center space-x-1 lg:space-x-2 8k:space-x-4 bg-slate-900/70 p-1 sm:p-1.5 8k:p-2.5 rounded-xl 8k:rounded-2xl border border-slate-800">
          {navItems.map((item) => (
            <button
              key={item.tab}
              onClick={() => handleSelectTab(item.tab)}
              className={`flex items-center space-x-1.5 lg:space-x-2 8k:space-x-3 px-3 py-1.5 lg:px-4 lg:py-2 8k:px-6 8k:py-3.5 rounded-lg 8k:rounded-xl text-xs lg:text-sm 8k:text-xl font-medium whitespace-nowrap transition-all ${
                currentTab === item.tab
                  ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              {item.icon}
              <span>{t(item.labelKey)}</span>
            </button>
          ))}
        </nav>

        {/* Actions & Utilities */}
        <div className="flex items-center space-x-2 8k:space-x-4">
          {/* Language Selector */}
          <div className="flex items-center space-x-1 bg-slate-900/80 border border-slate-800 px-2 py-1 sm:px-2.5 sm:py-1.5 8k:px-4 8k:py-2 rounded-lg 8k:rounded-xl text-xs 8k:text-lg">
            <Globe className="w-3.5 h-3.5 8k:w-6 8k:h-6 text-slate-400" />
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value as SupportedLanguage)}
              className="bg-transparent text-slate-300 text-xs 8k:text-lg font-mono font-semibold focus:outline-none cursor-pointer"
              aria-label="Language"
            >
              <option value="it" className="bg-slate-900 text-slate-200">IT</option>
              <option value="en" className="bg-slate-900 text-slate-200">EN</option>
              <option value="fr" className="bg-slate-900 text-slate-200">FR</option>
            </select>
          </div>

          {/* Security & Mesh Badges */}
          <div className="hidden lg:flex items-center space-x-2 bg-slate-950/60 border border-slate-800 px-2.5 py-1 8k:px-4 8k:py-2 rounded-lg 8k:rounded-xl text-xs 8k:text-lg font-mono">
            <ShieldCheck className="w-3.5 h-3.5 8k:w-6 8k:h-6 text-emerald-400" />
            <span className="text-emerald-400 font-bold">{t('nav_zero_trust')}</span>
          </div>

          <div className="hidden xl:flex items-center space-x-2 bg-slate-950/60 border border-slate-800 px-2.5 py-1 8k:px-4 8k:py-2 rounded-lg 8k:rounded-xl text-xs 8k:text-lg font-mono">
            <Cpu className="w-3.5 h-3.5 8k:w-6 8k:h-6 text-cyan-400" />
            <span className={isMeshConnected ? "text-cyan-400 font-semibold" : "text-amber-400 font-semibold"}>
              {isMeshConnected ? t('nav_mesh_connected') : t('nav_mesh_solo')}
            </span>
          </div>

          {/* Mobile Menu Hamburger */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-xl bg-slate-900/80 border border-slate-800 text-slate-300 hover:text-white"
            aria-label={t('nav_menu_toggle')}
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Dropdown / Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden mt-2.5 pt-2 border-t border-slate-800/80 pb-3 flex flex-col space-y-1.5 animate-fadeIn">
          {navItems.map((item) => (
            <button
              key={item.tab}
              onClick={() => handleSelectTab(item.tab)}
              className={`w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                currentTab === item.tab
                  ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-300 hover:bg-slate-800/50'
              }`}
            >
              {item.icon}
              <span>{t(item.labelKey)}</span>
            </button>
          ))}
          <div className="pt-2 flex items-center justify-between px-3 text-[11px] font-mono text-slate-400">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <ShieldCheck className="w-3 h-3" /> {t('nav_zero_trust')}
            </span>
            <span className={isMeshConnected ? "text-cyan-400" : "text-amber-400"}>
              {isMeshConnected ? t('nav_mesh_connected') : t('nav_mesh_solo')}
            </span>
          </div>
        </div>
      )}
    </header>
  );
};
