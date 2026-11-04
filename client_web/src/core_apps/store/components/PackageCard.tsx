import React from 'react';
import {
  CheckCircle2,
  Trash2,
  Download,
  Brain,
  Eye,
  Mic,
  Briefcase,
  Server,
  Sparkles
} from 'lucide-react';
import { StorePackage } from '../types';

interface PackageCardProps {
  pkg: StorePackage;
  isBusy: boolean;
  isSelected?: boolean;
  onToggleSelect?: (pkg: StorePackage) => void;
  onInstall: (pkg: StorePackage) => void;
  onUninstall: (pkg: StorePackage) => void;
  t: (key: string, params?: Record<string, any>) => string;
}

export const PackageCard: React.FC<PackageCardProps> = ({
  pkg,
  isBusy,
  isSelected = false,
  onToggleSelect,
  onInstall,
  onUninstall,
  t
}) => {
  const getCategoryTheme = (category: string) => {
    switch (category) {
      case 'intelligence':
        return { icon: Brain, color: 'text-indigo-400', bg: 'bg-indigo-500/10 border-indigo-500/20' };
      case 'vision':
        return { icon: Eye, color: 'text-sky-400', bg: 'bg-sky-500/10 border-sky-500/20' };
      case 'audio':
        return { icon: Mic, color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20' };
      case 'productivity':
        return { icon: Briefcase, color: 'text-teal-400', bg: 'bg-teal-500/10 border-teal-500/20' };
      case 'system':
        return { icon: Server, color: 'text-slate-400', bg: 'bg-slate-500/10 border-slate-500/20' };
      default:
        return { icon: Sparkles, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' };
    }
  };

  const getHardwareBadge = (sizeGb: number) => {
    if (sizeGb < 1.0) {
      return { label: t('badge_light'), className: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' };
    }
    if (sizeGb < 4.0) {
      return { label: t('badge_moderate'), className: 'bg-sky-500/10 text-sky-400 border-sky-500/30' };
    }
    return { label: t('badge_intensive'), className: 'bg-purple-500/10 text-purple-400 border-purple-500/30' };
  };

  const theme = getCategoryTheme(pkg.category);
  const CategoryIcon = theme.icon;
  const badge = getHardwareBadge(pkg.size_gb);
  const isCustom = pkg.source === 'custom';

  return (
    <div className={`os-card os-card-interactive group ${isSelected ? 'os-card-selected' : ''}`}>
      <div>
        <div className="flex items-start justify-between gap-3 mb-2.5">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center border shadow-xs transition-transform group-hover:scale-105 ${theme.bg} ${theme.color}`}>
              <CategoryIcon className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-sm text-[var(--md-sys-color-on-surface)] group-hover:text-[var(--md-sys-color-primary)] transition-colors">
                  {pkg.title}
                </h3>
              </div>
              <div className="flex items-center gap-1.5 mt-1">
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border ${badge.className}`}>
                  {badge.label}
                </span>
                <span className="text-[10px] font-mono text-[var(--md-sys-color-on-surface-variant)]">
                  {t('size_label', { gb: pkg.size_gb })}
                </span>
                {isCustom ? (
                  <span className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/30">
                    {pkg.repository_name || t('repo_custom_badge')}
                  </span>
                ) : (
                  <span className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-[var(--md-sys-color-surface-container-high)] text-[var(--md-sys-color-on-surface-variant)] border border-[var(--md-sys-color-outline-variant)]">
                    {t('repo_official_badge')}
                  </span>
                )}
              </div>
            </div>
          </div>

          {!pkg.installed && onToggleSelect && (
            <label
              className="os-checkbox-wrapper"
              onClick={e => e.stopPropagation()}
            >
              <input
                type="checkbox"
                className="os-checkbox-input"
                checked={isSelected}
                onChange={() => onToggleSelect(pkg)}
              />
              <div className="os-checkbox-box">
                <CheckCircle2 className="os-checkbox-tick" />
              </div>
            </label>
          )}
        </div>

        <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed line-clamp-3 mb-4 mt-2">
          {pkg.description}
        </p>
      </div>

      <div className="pt-3 border-t border-[var(--md-sys-color-outline-variant)] flex items-center justify-between gap-2.5">
        {pkg.installed ? (
          <>
            <div className="flex items-center gap-1.5 text-emerald-400 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{t('installed')}</span>
            </div>
            {pkg.removable ? (
              <button
                type="button"
                onClick={() => onUninstall(pkg)}
                disabled={isBusy}
                className="os-btn os-btn-ghost text-rose-400 hover:text-rose-300 py-1 px-2.5 text-xs"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{isBusy ? t('uninstalling') : t('uninstall')}</span>
              </button>
            ) : (
              <span className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] font-medium">
                {t('core_package')}
              </span>
            )}
          </>
        ) : (
          <button
            type="button"
            onClick={() => onInstall(pkg)}
            disabled={isBusy}
            className="os-btn os-btn-primary w-full py-2 text-xs"
          >
            <Download className={`w-3.5 h-3.5 ${isBusy ? 'animate-bounce' : ''}`} />
            <span>{isBusy ? t('installing') : t('install')}</span>
          </button>
        )}
      </div>
    </div>
  );
};
