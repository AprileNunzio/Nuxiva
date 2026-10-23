import React, { useMemo, useState } from 'react';
import { useI18n } from '../shared/i18n/I18nContext';
import { useScopedI18n, getScopedString } from '../shared/i18n/useScopedI18n';
import { useResource } from './shared/useResource';
import { FeaturesOverview } from './shared/featureTypes';
import {
  Clock, Users, Binary, Hand, Workflow, Grid, Home, Music, Mail, Tv,
  Scale, Server, Video, ShieldCheck, Zap, Lock, UserCheck, FileText,
  Box, BookOpen, AlertTriangle, Archive, Radio, RefreshCw, ArrowRight,
  Search, X, Brain, Shield, Layers, LayoutGrid, ListFilter, Cpu, Activity, Mic
} from 'lucide-react';

export type CoreAppCategory = 'all' | 'ai' | 'infra' | 'automation' | 'security' | 'media';

export interface CoreAppDef {
  id: string;
  iconName: string;
  category: Exclude<CoreAppCategory, 'all'>;
  accent: 'purple' | 'cyan' | 'amber' | 'rose' | 'emerald';
}

export const CATEGORIES: {
  id: CoreAppCategory;
  label: Record<string, string>;
  icon: React.ElementType;
  accent: string;
  borderActive: string;
  bgActive: string;
  badgeColor: string;
}[] = [
  {
    id: 'all',
    label: { it: 'Tutti i Moduli', en: 'All Modules', es: 'Todos los Módulos', fr: 'Tous les Modules' },
    icon: Grid,
    accent: 'text-cyan-400',
    borderActive: 'border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.3)]',
    bgActive: 'bg-cyan-500/15 text-white',
    badgeColor: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
  },
  {
    id: 'ai',
    label: { it: 'Intelligenza & Agenti', en: 'AI & Agents', es: 'IA y Agentes', fr: 'IA et Agents' },
    icon: Brain,
    accent: 'text-purple-400',
    borderActive: 'border-purple-500 shadow-[0_0_15px_rgba(168,85,247,0.3)]',
    bgActive: 'bg-purple-500/15 text-white',
    badgeColor: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  },
  {
    id: 'infra',
    label: { it: 'Infrastruttura & Mesh', en: 'Infra & Mesh', es: 'Infraestructura y Malla', fr: 'Infrastructure et Mesh' },
    icon: Server,
    accent: 'text-cyan-400',
    borderActive: 'border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.3)]',
    bgActive: 'bg-cyan-500/15 text-white',
    badgeColor: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
  },
  {
    id: 'automation',
    label: { it: 'Automazione & Flussi', en: 'Automation & Ops', es: 'Automatización y Flujos', fr: 'Automatisation & Flux' },
    icon: Zap,
    accent: 'text-amber-400',
    borderActive: 'border-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.3)]',
    bgActive: 'bg-amber-500/15 text-white',
    badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  },
  {
    id: 'security',
    label: { it: 'Sicurezza & Sorveglianza', en: 'Security & Space', es: 'Seguridad y Espacio', fr: 'Sécurité & Espace' },
    icon: Shield,
    accent: 'text-rose-400',
    borderActive: 'border-rose-500 shadow-[0_0_15px_rgba(244,63,94,0.3)]',
    bgActive: 'bg-rose-500/15 text-white',
    badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
  },
  {
    id: 'media',
    label: { it: 'Produttività & Media', en: 'Productivity & Media', es: 'Productividad y Medios', fr: 'Productivité & Médias' },
    icon: Layers,
    accent: 'text-emerald-400',
    borderActive: 'border-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.3)]',
    bgActive: 'bg-emerald-500/15 text-white',
    badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  },
];

const CORE_APPS_LIST: CoreAppDef[] = [
  { id: 'agents', iconName: 'Users', category: 'ai', accent: 'purple' },
  { id: 'hippocampus_router', iconName: 'Brain', category: 'ai', accent: 'purple' },
  { id: 'algorithms', iconName: 'Binary', category: 'ai', accent: 'purple' },
  { id: 'ear_log', iconName: 'Mic', category: 'ai', accent: 'purple' },
  { id: 'study', iconName: 'BookOpen', category: 'ai', accent: 'purple' },
  { id: 'twin', iconName: 'Box', category: 'ai', accent: 'purple' },
  { id: 'nodes', iconName: 'Server', category: 'infra', accent: 'cyan' },
  { id: 'vpn', iconName: 'Radio', category: 'infra', accent: 'cyan' },
  { id: 'firewall', iconName: 'ShieldCheck', category: 'infra', accent: 'cyan' },
  { id: 'updater', iconName: 'RefreshCw', category: 'infra', accent: 'cyan' },
  { id: 'backup', iconName: 'Archive', category: 'infra', accent: 'cyan' },
  { id: 'automations', iconName: 'Zap', category: 'automation', accent: 'amber' },
  { id: 'flows', iconName: 'Workflow', category: 'automation', accent: 'amber' },
  { id: 'hands', iconName: 'Hand', category: 'automation', accent: 'amber' },
  { id: 'laws', iconName: 'Scale', category: 'automation', accent: 'amber' },
  { id: 'emergency', iconName: 'AlertTriangle', category: 'security', accent: 'rose' },
  { id: 'vault', iconName: 'Lock', category: 'security', accent: 'rose' },
  { id: 'places', iconName: 'Home', category: 'security', accent: 'rose' },
  { id: 'cameras', iconName: 'Video', category: 'security', accent: 'rose' },
  { id: 'office', iconName: 'FileText', category: 'media', accent: 'emerald' },
  { id: 'google', iconName: 'Mail', category: 'media', accent: 'emerald' },
  { id: 'features_hub', iconName: 'Grid', category: 'media', accent: 'emerald' },
];

const ICON_MAP: Record<string, React.ReactNode> = {
  Brain: <Brain className="w-5 h-5 text-purple-400" />,
  Clock: <Clock className="w-5 h-5 text-amber-400" />,
  Users: <Users className="w-5 h-5 text-purple-400" />,
  Binary: <Binary className="w-5 h-5 text-purple-400" />,
  Hand: <Hand className="w-5 h-5 text-amber-400" />,
  Workflow: <Workflow className="w-5 h-5 text-amber-400" />,
  Grid: <Grid className="w-5 h-5 text-emerald-400" />,
  Home: <Home className="w-5 h-5 text-rose-400" />,
  Music: <Music className="w-5 h-5 text-emerald-400" />,
  Mail: <Mail className="w-5 h-5 text-emerald-400" />,
  Tv: <Tv className="w-5 h-5 text-emerald-400" />,
  Scale: <Scale className="w-5 h-5 text-amber-400" />,
  Mic: <Mic className="w-5 h-5 text-purple-400" />,
  Server: <Server className="w-5 h-5 text-cyan-400" />,
  Video: <Video className="w-5 h-5 text-rose-400" />,
  ShieldCheck: <ShieldCheck className="w-5 h-5 text-cyan-400" />,
  Zap: <Zap className="w-5 h-5 text-amber-400" />,
  Lock: <Lock className="w-5 h-5 text-rose-400" />,
  UserCheck: <UserCheck className="w-5 h-5 text-rose-400" />,
  FileText: <FileText className="w-5 h-5 text-emerald-400" />,
  Box: <Box className="w-5 h-5 text-purple-400" />,
  BookOpen: <BookOpen className="w-5 h-5 text-purple-400" />,
  AlertTriangle: <AlertTriangle className="w-5 h-5 text-rose-500 animate-pulse" />,
  Archive: <Archive className="w-5 h-5 text-cyan-400" />,
  Radio: <Radio className="w-5 h-5 text-cyan-400" />,
  RefreshCw: <RefreshCw className="w-5 h-5 text-cyan-400" />,
};

const ACCENT_STYLES: Record<string, {
  border: string;
  hoverBorder: string;
  shadow: string;
  badge: string;
  iconBg: string;
}> = {
  purple: {
    border: 'border-purple-900/40',
    hoverBorder: 'hover:border-purple-500/60',
    shadow: 'hover:shadow-[0_0_20px_rgba(168,85,247,0.2)]',
    badge: 'bg-purple-950/60 text-purple-300 border-purple-800/80',
    iconBg: 'bg-purple-950/30 border-purple-800/40',
  },
  cyan: {
    border: 'border-cyan-900/40',
    hoverBorder: 'hover:border-cyan-500/60',
    shadow: 'hover:shadow-[0_0_20px_rgba(6,182,212,0.2)]',
    badge: 'bg-cyan-950/60 text-cyan-300 border-cyan-800/80',
    iconBg: 'bg-cyan-950/30 border-cyan-800/40',
  },
  amber: {
    border: 'border-amber-900/40',
    hoverBorder: 'hover:border-amber-500/60',
    shadow: 'hover:shadow-[0_0_20px_rgba(245,158,11,0.2)]',
    badge: 'bg-amber-950/60 text-amber-300 border-amber-800/80',
    iconBg: 'bg-amber-950/30 border-amber-800/40',
  },
  rose: {
    border: 'border-rose-900/40',
    hoverBorder: 'hover:border-rose-500/60',
    shadow: 'hover:shadow-[0_0_20px_rgba(244,63,94,0.2)]',
    badge: 'bg-rose-950/60 text-rose-300 border-rose-800/80',
    iconBg: 'bg-rose-950/30 border-rose-800/40',
  },
  emerald: {
    border: 'border-emerald-900/40',
    hoverBorder: 'hover:border-emerald-500/60',
    shadow: 'hover:shadow-[0_0_20px_rgba(16,185,129,0.2)]',
    badge: 'bg-emerald-950/60 text-emerald-300 border-emerald-800/80',
    iconBg: 'bg-emerald-950/30 border-emerald-800/40',
  },
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
  const style = ACCENT_STYLES[app.accent] || ACCENT_STYLES.cyan;

  return (
    <div
      onClick={() => onSelect(app.id)}
      className={`group relative backdrop-blur-xl bg-slate-900/70 hover:bg-slate-900/95 border ${style.border} ${style.hoverBorder} ${style.shadow} rounded-xl p-3.5 cursor-pointer transition-all duration-200 hover:scale-[1.015] flex flex-col justify-between`}
    >
      <div>
        <div className="flex items-center justify-between mb-2.5">
          <div className={`w-9 h-9 rounded-lg ${style.iconBg} border flex items-center justify-center transition-transform group-hover:scale-105`}>
            {ICON_MAP[app.iconName] || <Grid className="w-5 h-5 text-cyan-400" />}
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-md border font-semibold tracking-wider ${style.badge}`}>
              {app.id}
            </span>
          </div>
        </div>

        <h3 className="text-sm font-bold text-white group-hover:text-cyan-300 transition-colors truncate">
          {title}
        </h3>
        <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">
          {description}
        </p>
      </div>

      <div className="mt-3 pt-2.5 border-t border-slate-800/70 flex items-center justify-between text-[11px] font-mono text-slate-400 group-hover:text-cyan-300 transition-colors">
        <span className="font-semibold">{openLabel}</span>
        <ArrowRight className="w-3.5 h-3.5 transform group-hover:translate-x-1 transition-transform" />
      </div>
    </div>
  );
};

export const GlobalCommandGrid: React.FC<{
  onSelectApp?: (appId: string) => void;
  onBackToCanvas?: () => void;
}> = ({ onSelectApp, onBackToCanvas }) => {
  const { lang } = useI18n();
  const { t } = useScopedI18n('app_shell/command_grid');
  const features = useResource<FeaturesOverview>('/api/features', 30000);
  const running = features.data ? features.data.features.filter((item) => item.state.enabled).length : null;
  const [selectedCategory, setSelectedCategory] = useState<CoreAppCategory>('all');
  const [search, setSearch] = useState('');
  const [viewMode, setViewMode] = useState<'grouped' | 'dense'>('grouped');
  const processedApps = useMemo(() => {
    const collator = new Intl.Collator(lang, { sensitivity: 'base' });
    const items = CORE_APPS_LIST.map((app) => {
      const translatedTitle = getScopedString(`core_apps/${app.id}`, lang, 'title', app.id);
      const translatedDesc = getScopedString(`core_apps/${app.id}`, lang, 'description', '');
      return {
        ...app,
        translatedTitle,
        translatedDesc,
      };
    });
    const query = search.trim().toLowerCase();
    const filtered = items.filter((app) => {
      const matchesCategory = selectedCategory === 'all' || app.category === selectedCategory;
      if (!matchesCategory) return false;

      if (!query) return true;
      return (
        app.id.toLowerCase().includes(query) ||
        app.translatedTitle.toLowerCase().includes(query) ||
        app.translatedDesc.toLowerCase().includes(query)
      );
    });
    return filtered.sort((a, b) => collator.compare(a.translatedTitle, b.translatedTitle));
  }, [lang, selectedCategory, search]);
  const categoryCounts = useMemo(() => {
    const counts: Record<CoreAppCategory, number> = {
      all: CORE_APPS_LIST.length,
      ai: 0,
      infra: 0,
      automation: 0,
      security: 0,
      media: 0,
    };
    CORE_APPS_LIST.forEach((app) => {
      counts[app.category] = (counts[app.category] || 0) + 1;
    });
    return counts;
  }, []);

  return (
    <div className="w-full min-h-[calc(100vh-68px)] bg-[#030712] p-5 lg:p-8 font-sans text-slate-100 flex flex-col gap-5">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-xl lg:text-2xl font-black tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-teal-300 to-blue-500">
              {t('heading')}
            </h1>
            {running !== null && (
              <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 text-xs font-mono font-bold">
                <Activity className="w-3.5 h-3.5 animate-pulse text-cyan-400" />
                <span>{t('active_services', { count: running })}</span>
              </div>
            )}
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[11px] font-mono font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>{t('zero_trust')}</span>
            </div>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            {t('subtitle')}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('search_placeholder')}
              aria-label={t('search_placeholder')}
              className="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl pl-9 pr-8 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-mono transition"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                aria-label={t('clear')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          {selectedCategory === 'all' && !search && (
            <div className="hidden md:flex items-center bg-slate-900 border border-slate-800 rounded-xl p-0.5">
              <button
                onClick={() => setViewMode('grouped')}
                title={t('view_grouped')}
                className={`p-1.5 rounded-lg transition ${
                  viewMode === 'grouped' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-white'
                }`}
              >
                <ListFilter className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('dense')}
                title={t('view_dense')}
                className={`p-1.5 rounded-lg transition ${
                  viewMode === 'dense' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-white'
                }`}
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
            </div>
          )}

          {onBackToCanvas && (
            <button
              onClick={onBackToCanvas}
              className="px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs text-slate-200 hover:text-white transition flex items-center gap-1.5 shrink-0 cursor-pointer font-mono"
            >
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              <span className="hidden sm:inline">{t('spatial_graph')}</span>
            </button>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
        {CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          const isActive = selectedCategory === cat.id;
          const label = cat.label[lang] || cat.label.it;
          const count = categoryCounts[cat.id];

          return (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl border text-xs font-semibold transition-all duration-200 shrink-0 cursor-pointer ${
                isActive
                  ? `${cat.borderActive} ${cat.bgActive} font-bold`
                  : 'bg-slate-900/60 border-slate-800/80 text-slate-400 hover:text-slate-200 hover:border-slate-700'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? cat.accent : 'text-slate-400'}`} />
              <span>{label}</span>
              <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full border ${
                isActive ? cat.badgeColor : 'bg-slate-800 text-slate-500 border-slate-700'
              }`}>
                {count}
              </span>
            </button>
          );
        })}
      </div>
      {processedApps.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border border-slate-800 bg-slate-900/40 text-slate-400 flex flex-col items-center justify-center gap-3">
          <Search className="w-8 h-8 text-slate-600" />
          <p className="text-sm">{t('no_results', { query: search })}</p>
          <button
            onClick={() => { setSearch(''); setSelectedCategory('all'); }}
            className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold"
          >
            {t('reset_filters')}
          </button>
        </div>
      ) : selectedCategory === 'all' && viewMode === 'grouped' && !search ? (
        <div className="space-y-6">
          {CATEGORIES.filter((c) => c.id !== 'all').map((cat) => {
            const groupApps = processedApps.filter((a) => a.category === cat.id);
            if (groupApps.length === 0) return null;
            const Icon = cat.icon;
            const label = cat.label[lang] || cat.label.it;

            return (
              <div key={cat.id} className="space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800/60 pb-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1 rounded-lg bg-slate-900 border border-slate-800">
                      <Icon className={`w-4 h-4 ${cat.accent}`} />
                    </div>
                    <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                      {label}
                    </h2>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${cat.badgeColor}`}>
                      {groupApps.length}
                    </span>
                  </div>
                  <button
                    onClick={() => setSelectedCategory(cat.id)}
                    className="text-[11px] font-mono text-cyan-400 hover:text-cyan-300 transition"
                  >
                    {t('see_all')} &rarr;
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 3xl:grid-cols-6 4xl:grid-cols-8 5xl:grid-cols-10 gap-3.5">
                  {groupApps.map((app) => (
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
          })}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 3xl:grid-cols-7 4xl:grid-cols-8 5xl:grid-cols-10 gap-3.5">
          {processedApps.map((app) => (
            <CoreAppCard
              key={app.id}
              app={app}
              lang={lang}
              onSelect={(id) => onSelectApp && onSelectApp(id)}
            />
          ))}
        </div>
      )}
    </div>
  );
};
