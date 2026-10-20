import React from 'react';
import { BrainTargetConfig } from '../types';
import {
  Zap,
  Brain,
  Mic,
  Crown,
  Code,
  Search,
  ShieldAlert,
  Home,
  Tv,
  GraduationCap,
  Share2,
  Compass,
  Key,
  HardDrive,
  Server,
  ArrowRight,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Wrench,
} from 'lucide-react';

interface TargetCardProps {
  readonly target: BrainTargetConfig;
  readonly isHero?: boolean;
  readonly onConfigure: (target: BrainTargetConfig) => void;
  readonly t: (key: string) => string;
}

export const TargetCard: React.FC<TargetCardProps> = ({ target, isHero = false, onConfigure, t }) => {
  const renderIcon = () => {
    switch (target.avatarIcon) {
      case 'Zap':
        return <Zap className={isHero ? 'w-7 h-7' : 'w-5 h-5'} />;
      case 'Brain':
        return <Brain className={isHero ? 'w-7 h-7' : 'w-5 h-5'} />;
      case 'Mic':
        return <Mic className={isHero ? 'w-6 h-6' : 'w-5 h-5'} />;
      case 'Crown':
        return <Crown className={isHero ? 'w-6 h-6' : 'w-5 h-5'} />;
      case 'Code':
        return <Code className="w-5 h-5" />;
      case 'Search':
        return <Search className="w-5 h-5" />;
      case 'ShieldAlert':
        return <ShieldAlert className="w-5 h-5" />;
      case 'Home':
        return <Home className="w-5 h-5" />;
      case 'Tv':
        return <Tv className="w-5 h-5" />;
      case 'GraduationCap':
        return <GraduationCap className="w-5 h-5" />;
      case 'Share2':
        return <Share2 className="w-5 h-5" />;
      case 'Compass':
        return <Compass className="w-5 h-5" />;
      default:
        return <Brain className="w-5 h-5" />;
    }
  };

  const getMethodBadge = () => {
    switch (target.method) {
      case 'api_key':
        return {
          icon: <Key className="w-3.5 h-3.5" />,
          label: 'API Key',
          detail: target.providerId ? target.providerId.toUpperCase() : 'Cloud',
          badgeClass: 'bg-amber-100 text-amber-950 border border-amber-300 font-bold',
        };
      case 'ollama_remote':
        return {
          icon: <Server className="w-3.5 h-3.5" />,
          label: 'Ollama Remoto',
          detail: target.remoteHost || 'LAN',
          badgeClass: 'bg-purple-100 text-purple-950 border border-purple-300 font-bold',
        };
      case 'ollama_local':
        return {
          icon: <HardDrive className="w-3.5 h-3.5" />,
          label: 'Ollama Locale',
          detail: 'Host',
          badgeClass: 'bg-emerald-100 text-emerald-950 border border-emerald-300 font-bold',
        };
    }
  };

  const badge = getMethodBadge();

  // MD3 Expressive Light Theme Styles
  const getExpressiveTheme = () => {
    if (target.id === 'fast_conversation') {
      return {
        card: 'bg-gradient-to-br from-blue-50/80 via-white to-cyan-50/40 border-2 border-blue-200 hover:border-blue-500 shadow-md hover:shadow-xl',
        iconBg: 'bg-blue-600 text-white shadow-md shadow-blue-500/25',
        titleColor: 'text-slate-950',
        llmBox: 'bg-white/95 border border-blue-200/90 shadow-2xs',
        llmText: 'text-blue-950',
      };
    }
    if (target.id === 'reasoning') {
      return {
        card: 'bg-gradient-to-br from-indigo-50/80 via-white to-purple-50/40 border-2 border-indigo-200 hover:border-indigo-500 shadow-md hover:shadow-xl',
        iconBg: 'bg-indigo-600 text-white shadow-md shadow-indigo-500/25',
        titleColor: 'text-slate-950',
        llmBox: 'bg-white/95 border border-indigo-200/90 shadow-2xs',
        llmText: 'text-indigo-950',
      };
    }
    if (target.id === 'live_audio') {
      return {
        card: 'bg-gradient-to-br from-emerald-50/80 via-white to-teal-50/40 border-2 border-emerald-200 hover:border-emerald-500 shadow-md hover:shadow-xl',
        iconBg: 'bg-emerald-600 text-white shadow-md shadow-emerald-500/25',
        titleColor: 'text-slate-950',
        llmBox: 'bg-white/95 border border-emerald-200/90 shadow-2xs',
        llmText: 'text-emerald-950',
      };
    }
    if (target.id === 'ceo') {
      return {
        card: 'bg-gradient-to-br from-slate-100/90 via-white to-indigo-50/40 border-2 border-slate-300 hover:border-indigo-500 shadow-md hover:shadow-xl',
        iconBg: 'bg-slate-900 text-white shadow-md shadow-slate-900/25',
        titleColor: 'text-slate-950',
        llmBox: 'bg-white/95 border border-slate-300/90 shadow-2xs',
        llmText: 'text-slate-950',
      };
    }
    // Generic Agent
    return {
      card: 'bg-white hover:bg-slate-50/80 border border-slate-200/90 hover:border-indigo-400 shadow-2xs hover:shadow-lg',
      iconBg: 'bg-slate-100 text-slate-800 border border-slate-200 shadow-2xs',
      titleColor: 'text-slate-950',
      llmBox: 'bg-slate-50/90 border border-slate-200/90',
      llmText: 'text-slate-900',
    };
  };

  const theme = getExpressiveTheme();

  return (
    <div
      onClick={() => onConfigure(target)}
      role="button"
      tabIndex={0}
      aria-label={`${target.name} - ${target.assignedModel}`}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onConfigure(target);
        }
      }}
      className={`group relative overflow-hidden rounded-3xl transition-all duration-300 cursor-pointer flex flex-col justify-between ${
        theme.card
      } ${isHero ? 'p-6 sm:p-7' : 'p-5'}`}
    >
      <div>
        {/* Header row: Icon, Name, Category pill & Status */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3.5 min-w-0">
            <div
              className={`flex items-center justify-center rounded-2xl shrink-0 transition-transform duration-300 group-hover:scale-105 ${
                isHero ? 'w-14 h-14' : 'w-11 h-11'
              } ${theme.iconBg}`}
            >
              {renderIcon()}
            </div>

            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h3
                  className={`font-black tracking-tight truncate ${theme.titleColor} ${
                    isHero ? 'text-lg sm:text-xl' : 'text-sm sm:text-base'
                  }`}
                >
                  {target.name}
                </h3>
                {target.category === 'core_brain' && (
                  <span className="text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-100 text-blue-900 border border-blue-200">
                    {t('core_brain_badge')}
                  </span>
                )}
              </div>
              <p
                className={`mt-1 font-semibold leading-snug line-clamp-2 text-slate-600 ${
                  isHero ? 'text-xs sm:text-sm' : 'text-xs'
                }`}
              >
                {t(target.roleKey) || target.name}
              </p>
            </div>
          </div>

          {/* Operational Status Pill */}
          <div className="shrink-0">
            {target.status === 'connected' || target.status === 'ready' ? (
              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-900 bg-emerald-100 border border-emerald-300 px-2.5 py-1 rounded-full shadow-2xs">
                <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
                {t('status_ready')}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-950 bg-amber-100 border border-amber-300 px-2.5 py-1 rounded-full shadow-2xs">
                <AlertCircle className="w-3.5 h-3.5 text-amber-700" />
                {t('status_needs_config')}
              </span>
            )}
          </div>
        </div>

        {/* MD3 Light Container: Main LLM Assignment */}
        <div className={`mt-5 rounded-2xl p-4 transition-all ${theme.llmBox}`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block mb-0.5">
                {t('assigned_llm')}
              </span>
              <div
                className={`font-black tracking-tight truncate ${theme.llmText} ${
                  isHero ? 'text-base sm:text-lg' : 'text-xs sm:text-sm'
                }`}
              >
                {target.assignedModel}
              </div>
            </div>

            {/* Method pill */}
            <div className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full ${badge.badgeClass}`}>
              {badge.icon}
              <span>{badge.label}</span>
              <span className="opacity-40">•</span>
              <span>{badge.detail}</span>
            </div>
          </div>

          {/* Technical Specs: Context, Latency, MCP count */}
          <div className="mt-3.5 pt-3 border-t border-slate-200/90 grid grid-cols-3 gap-2 text-xs">
            <div>
              <span className="block text-[10px] uppercase font-bold text-slate-500">
                {t('context_window')}
              </span>
              <span className="font-black text-slate-900 mt-0.5 block truncate">
                {target.contextWindow || '128k token'}
              </span>
            </div>

            <div>
              <span className="block text-[10px] uppercase font-bold text-slate-500">
                {t('latency')}
              </span>
              <span className="font-black text-slate-900 mt-0.5 block">
                {target.latencyMs ? `${target.latencyMs} ms` : '~45 ms'}
              </span>
            </div>

            <div>
              <span className="block text-[10px] uppercase font-bold text-slate-500">
                {t('mcp_status')}
              </span>
              <span className="inline-flex items-center gap-1 font-black text-indigo-700 mt-0.5 truncate">
                <Wrench className="w-3 h-3 text-indigo-600" />
                {target.mcpToolsEnabled.length} {t('mcp_tools_active')}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Card Footer: Parameters and Action Button */}
      <div className="mt-5 pt-3 border-t border-slate-200/80 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-600">
          <Sliders className="w-3.5 h-3.5 text-indigo-600" />
          <span>Temp: <strong className="text-slate-900 font-bold">{target.temperature}</strong></span>
        </div>

        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onConfigure(target);
          }}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all ${
            isHero
              ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm shadow-indigo-600/20'
              : 'bg-slate-900 hover:bg-slate-800 text-white shadow-2xs'
          }`}
        >
          <span>{t('configure_step')}</span>
          <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
        </button>
      </div>
    </div>
  );
};
