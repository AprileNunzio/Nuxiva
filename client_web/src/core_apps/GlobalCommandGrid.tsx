import React, { useMemo, useState } from 'react';
import { useI18n } from '../shared/i18n/I18nContext';
import { useScopedI18n, getScopedString } from '../shared/i18n/useScopedI18n';
import {
  Clock, Users, Binary, Hand, Workflow, Grid, Home, Music, Mail, Tv,
  Scale, Server, Video, ShieldCheck, Zap, Lock, UserCheck, FileText,
  Box, BookOpen, AlertTriangle, Archive, Radio, RefreshCw, ArrowRight, Search, X
} from 'lucide-react';

interface CoreAppDef {
  id: string;
  iconName: string;
}

const CORE_APPS_LIST: CoreAppDef[] = [
  { id: 'habits', iconName: 'Clock' },
  { id: 'agents', iconName: 'Users' },
  { id: 'algorithms', iconName: 'Binary' },
  { id: 'hands', iconName: 'Hand' },
  { id: 'flows', iconName: 'Workflow' },
  { id: 'features_hub', iconName: 'Grid' },
  { id: 'places', iconName: 'Home' },
  { id: 'music', iconName: 'Music' },
  { id: 'google', iconName: 'Mail' },
  { id: 'iptv', iconName: 'Tv' },
  { id: 'laws', iconName: 'Scale' },
  { id: 'nodes', iconName: 'Server' },
  { id: 'cameras', iconName: 'Video' },
  { id: 'firewall', iconName: 'ShieldCheck' },
  { id: 'automations', iconName: 'Zap' },
  { id: 'vault', iconName: 'Lock' },
  { id: 'people', iconName: 'UserCheck' },
  { id: 'office', iconName: 'FileText' },
  { id: 'twin', iconName: 'Box' },
  { id: 'study', iconName: 'BookOpen' },
  { id: 'emergency', iconName: 'AlertTriangle' },
  { id: 'backup', iconName: 'Archive' },
  { id: 'vpn', iconName: 'Radio' },
  { id: 'updater', iconName: 'RefreshCw' },
];

const ICON_MAP: Record<string, React.ReactNode> = {
  Clock: <Clock className="w-6 h-6 text-cyan-400" />,
  Users: <Users className="w-6 h-6 text-purple-400" />,
  Binary: <Binary className="w-6 h-6 text-emerald-400" />,
  Hand: <Hand className="w-6 h-6 text-amber-400" />,
  Workflow: <Workflow className="w-6 h-6 text-blue-400" />,
  Grid: <Grid className="w-6 h-6 text-indigo-400" />,
  Home: <Home className="w-6 h-6 text-emerald-400" />,
  Music: <Music className="w-6 h-6 text-rose-400" />,
  Mail: <Mail className="w-6 h-6 text-red-400" />,
  Tv: <Tv className="w-6 h-6 text-cyan-400" />,
  Scale: <Scale className="w-6 h-6 text-yellow-400" />,
  Server: <Server className="w-6 h-6 text-cyan-400" />,
  Video: <Video className="w-6 h-6 text-teal-400" />,
  ShieldCheck: <ShieldCheck className="w-6 h-6 text-emerald-400" />,
  Zap: <Zap className="w-6 h-6 text-yellow-400" />,
  Lock: <Lock className="w-6 h-6 text-amber-400" />,
  UserCheck: <UserCheck className="w-6 h-6 text-blue-400" />,
  FileText: <FileText className="w-6 h-6 text-slate-300" />,
  Box: <Box className="w-6 h-6 text-purple-400" />,
  BookOpen: <BookOpen className="w-6 h-6 text-green-400" />,
  AlertTriangle: <AlertTriangle className="w-6 h-6 text-rose-500 animate-pulse" />,
  Archive: <Archive className="w-6 h-6 text-blue-400" />,
  Radio: <Radio className="w-6 h-6 text-purple-400" />,
  RefreshCw: <RefreshCw className="w-6 h-6 text-cyan-400" />,
};

interface CoreAppCardProps {
  app: CoreAppDef;
  onSelect: (appId: string) => void;
  lang: string;
}

const CoreAppCard: React.FC<CoreAppCardProps> = ({ app, onSelect }) => {
  const { t } = useScopedI18n(`core_apps/${app.id}`);
  const title = t('title');
  const description = t('description');
  const openLabel = t('open_app');

  return (
    <div
      onClick={() => onSelect(app.id)}
      className="group relative backdrop-blur-xl bg-slate-900/60 hover:bg-slate-900/90 border border-slate-800 hover:border-cyan-500/50 rounded-2xl p-5 cursor-pointer transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_0_25px_rgba(0,240,255,0.25)] flex flex-col justify-between"
    >
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="w-12 h-12 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-center group-hover:border-cyan-500/40 transition-colors">
            {ICON_MAP[app.iconName] || <Grid className="w-6 h-6 text-cyan-400" />}
          </div>
          <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-cyan-950/60 text-cyan-400 border border-cyan-800">
            {app.id}
          </span>
        </div>

        <h3 className="text-base font-bold text-white group-hover:text-cyan-300 transition-colors">
          {title}
        </h3>
        <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
          {description}
        </p>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono text-cyan-400 group-hover:text-cyan-300">
        <span>{openLabel}</span>
        <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
      </div>
    </div>
  );
};

export const GlobalCommandGrid: React.FC<{
  onSelectApp?: (appId: string) => void;
  onBackToCanvas?: () => void;
}> = ({ onSelectApp, onBackToCanvas }) => {
  const { lang, setLang } = useI18n();
  const [search, setSearch] = useState('');

  // Per ciascuna app leggiamo il titolo tradotto per la lingua corrente in modo da ordinare dinamicamente
  // tramite Intl.Collator(lang)
  const sortedApps = useMemo(() => {
    const collator = new Intl.Collator(lang, { sensitivity: 'base' });

    // Otteniamo per ogni app il titolo nella lingua attiva
    const itemsWithTitle = CORE_APPS_LIST.map((app) => {
      const translatedTitle = getScopedString(`core_apps/${app.id}`, lang, 'title', app.id);
      return {
        ...app,
        translatedTitle,
      };
    });

    return itemsWithTitle.sort((a, b) => {
      return collator.compare(a.translatedTitle, b.translatedTitle);
    });
  }, [lang]);

  return (
    <div className="w-full min-h-[calc(100vh-68px)] bg-[#030712] p-6 lg:p-10 font-mono text-slate-100 flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyan-950/60 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl lg:text-3xl font-bold tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">
              NUCLEO CENTRALE — GLOBAL COMMAND GRID
            </h1>
            <span className="px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 text-xs font-bold">
              24 APPLICATIVI (v5.0)
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Control Plane Logico Condiviso: ordinamento alfabetico runtime dinamico via Intl.Collator('{lang}').
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Selettore rapido lingua per testare ordinamento dinamico istantaneo */}
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-xl p-1 text-xs">
            {(['it', 'en', 'fr', 'es'] as const).map((code) => (
              <button
                key={code}
                onClick={() => setLang(code)}
                className={`px-3 py-1 rounded-lg uppercase font-bold transition-all ${
                  lang === code
                    ? 'bg-cyan-500 text-slate-950 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {code}
              </button>
            ))}
          </div>

          {onBackToCanvas && (
            <button
              onClick={onBackToCanvas}
              className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs text-white transition-all"
            >
              Torna al Grafo Spaziale
            </button>
          )}
        </div>
      </div>

      {/* Grid of 24 Core Apps */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
        {sortedApps.map((app) => (
          <CoreAppCard
            key={app.id}
            app={app}
            lang={lang}
            onSelect={(id) => onSelectApp && onSelectApp(id)}
          />
        ))}
      </div>
    </div>
  );
};
