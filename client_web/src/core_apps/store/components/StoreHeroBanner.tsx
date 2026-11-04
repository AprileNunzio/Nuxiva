import React from 'react';
import { Sparkles, Download, ArrowRight, Layers } from 'lucide-react';
import { StorePackage } from '../types';

interface StoreHeroBannerProps {
  featuredPackage: StorePackage | null;
  selectedCount: number;
  onOpenStepInstaller: () => void;
  onInstallFeatured: (pkg: StorePackage) => void;
  t: (key: string, params?: Record<string, any>) => string;
}

export const StoreHeroBanner: React.FC<StoreHeroBannerProps> = ({
  featuredPackage,
  selectedCount,
  onOpenStepInstaller,
  onInstallFeatured,
  t
}) => {
  return (
    <div className="relative mx-6 mt-4 p-6 rounded-2xl overflow-hidden border border-[var(--os-glass-border)] bg-gradient-to-r from-blue-900/40 via-indigo-900/30 to-slate-900/50 backdrop-blur-xl shadow-lg">
      <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 rounded-full bg-blue-500/20 blur-3xl pointer-events-none" />
      <div className="relative z-10 flex flex-wrap items-center justify-between gap-6">
        <div className="max-w-xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/15 border border-blue-400/25 text-blue-300 text-xs font-semibold mb-3">
            <Sparkles className="w-3.5 h-3.5" />
            <span>{t('store_spotlight_badge') || 'Nuxiva Modular Ecosystem'}</span>
          </div>
          <h2 className="text-xl font-bold tracking-tight text-[var(--md-sys-color-on-surface)] mb-1">
            {featuredPackage ? featuredPackage.title : (t('store_hero_heading') || 'Estendi il tuo Sistema Operativo')}
          </h2>
          <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
            {featuredPackage
              ? featuredPackage.description
              : (t('store_hero_subheading') || 'Installa pacchetti e componenti nativi con architettura modulare a step isolati e zero impatto sulle prestazioni.')}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {selectedCount > 0 && (
            <button
              type="button"
              className="os-btn os-btn-primary py-2.5 px-4 shadow-lg"
              onClick={onOpenStepInstaller}
            >
              <Layers className="w-4 h-4" />
              <span>
                {t('install_selected_batch') || 'Installa Selezionati'} ({selectedCount})
              </span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}

          {featuredPackage && !featuredPackage.installed && (
            <button
              type="button"
              className="os-btn os-btn-secondary py-2.5 px-4"
              onClick={() => onInstallFeatured(featuredPackage)}
            >
              <Download className="w-4 h-4" />
              <span>{t('quick_install') || 'Installazione Rapida'}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
