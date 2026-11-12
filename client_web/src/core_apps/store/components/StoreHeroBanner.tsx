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
    <div className="md-hero md-enter mx-6 mt-4 rounded-[1.75rem] p-6 shadow-[var(--md-elevation-1)]">
      <div className="relative z-10 flex flex-wrap items-center justify-between gap-6">
        <div className="max-w-xl">
          <div className="md-hero-tile mb-3 inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold text-primary">
            <Sparkles className="w-3.5 h-3.5" />
            <span>{t('store_spotlight_badge') || 'Nuxiva Modular Ecosystem'}</span>
          </div>
          <h2 className="mb-1 text-xl font-bold tracking-tight">
            {featuredPackage ? featuredPackage.title : (t('store_hero_heading') || 'Estendi il tuo Sistema Operativo')}
          </h2>
          <p className="md-hero-muted text-xs leading-relaxed">
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
