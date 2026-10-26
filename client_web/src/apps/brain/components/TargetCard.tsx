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
  RotateCcw,
} from 'lucide-react';

interface TargetCardProps {
  readonly target: BrainTargetConfig;
  readonly isHero?: boolean;
  readonly onConfigure: (target: BrainTargetConfig) => void;
  readonly onRestoreDefault?: (targetId: string) => void;
  readonly t: (key: string) => string;
}

export const TargetCard: React.FC<TargetCardProps> = ({
  target,
  isHero = false,
  onConfigure,
  onRestoreDefault,
  t,
}) => {
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

  const getExpressiveTheme = () => {
    if (target.id === 'fast_conversation') {
      return {
        card: 'bg-gradient-to-br from-blue-50/80 via-white to-cyan-50/40 border-2 border-blue-200 hover:border-blue-500 shadow-xs hover:shadow-md',
        iconBg: 'bg-blue-600 text-white shadow-xs',
        titleColor: 'text-slate-950',
        llmBox: 'bg-white/95 border border-blue-200/90 shadow-2xs',
        llmText: 'text-blue-950',
      };
    }
    if (target.id === 'reasoning') {
      return {
        card: 'bg-gradient-to-br from-indigo-50/80 via-white to-purple-50/40 border-2 border-indigo-200 hover:border-indigo-500 shadow-xs hover:shadow-md',
        iconBg: 'bg-indigo-600 text-white shadow-xs',
        titleColor: 'text-slate-950',
        llmBox: 'bg-white/95 border border-indigo-200/90 shadow-2xs',
        llmText: 'text-indigo-950',
      };
    }
    if (target.id === 'live_audio') {
      return {
        card: 'bg-gradient-to-br from-emerald-50/80 via-white to-teal-50/40 border-2 border-emerald-200 hover:border-emerald-500 shadow-xs hover:shadow-md',
        iconBg: 'bg-emerald-600 text-white shadow-xs',
        titleColor: 'text-slate-950',
        llmBox: 'bg-white/95 border border-emerald-200/90 shadow-2xs',
        llmText: 'text-emerald-950',
      };
    }
    if (target.id === 'ceo') {
      return {
        card: 'bg-gradient-to-br from-slate-100/90 via-white to-indigo-50/40 border-2 border-slate-300 hover:border-indigo-500 shadow-xs hover:shadow-md',
        iconBg: 'bg-slate-900 text-white shadow-xs',
        titleColor: 'text-slate-950',
        llmBox: 'bg-white/95 border border-slate-300/90 shadow-2xs',
        llmText: 'text-slate-950',
      };
    }
    return {
      card: 'bg-white hover:bg-slate-50/80 border border-slate-200/90 hover:border-indigo-400 shadow-2xs hover:shadow-sm',
      iconBg: 'bg-slate-100 text-slate-800 border border-slate-200 shadow-2xs',
      titleColor: 'text-slate-950',
      llmBox: 'bg-slate-50/90 border border-slate-200/90',
      llmText: 'text-slate-900',
    };
  };

  const theme = getExpressiveTheme();

  return (
    <div
      className={`group relative overflow-hidden rounded-3xl transition-all duration-300 flex flex-col justify-between ${
        theme.card
      } ${isHero ? 'p-6 sm:p-7' : 'p-5'}`}
    >
      <div>
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

          <div className="shrink-0 flex items-center gap-2">
            {target.inheritsGlobalDefault ? (
              <span className="inline-flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-900 border border-emerald-300 shadow-2xs">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                {t('synchronized_with_global_badge')}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full bg-amber-100 text-amber-950 border border-amber-300 shadow-2xs">
                <Sliders className="w-3.5 h-3.5 text-amber-700 shrink-0" />
                {t('custom_override_badge')}
              </span>
            )}
          </div>
        </div>

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

            <div className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full ${badge.badgeClass}`}>
              {badge.icon}
              <span>{badge.label}</span>
              <span className="opacity-40">•</span>
              <span>{badge.detail}</span>
            </div>
          </div>

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
              <span className="font-black text-emerald-700 mt-0.5 block">
                {target.latencyMs || 25} {t('latency_ms')}
              </span>
            </div>

            <div>
              <span className="block text-[10px] uppercase font-bold text-slate-500">
                {t('mcp_status')}
              </span>
              <span className="font-black text-indigo-700 mt-0.5 block truncate">
                {target.mcpToolsEnabled.length} {t('mcp_tools_active')}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
        {!target.inheritsGlobalDefault && onRestoreDefault && (
          <button
            type="button"
            onClick={() => onRestoreDefault(target.id)}
            className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-600 hover:text-indigo-600 transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            {t('restore_global_default_btn')}
          </button>
        )}

        <button
          type="button"
          onClick={() => onConfigure(target)}
          className="ml-auto inline-flex items-center gap-1.5 text-xs font-black text-indigo-600 hover:text-indigo-700 group-hover:translate-x-0.5 transition"
        >
          <span>{t('configure_step')}</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
