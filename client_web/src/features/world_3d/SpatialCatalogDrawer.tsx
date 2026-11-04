import React, { useState } from 'react';
import { 
  Sparkles, 
  Layers, 
  Trash2, 
  Umbrella, 
  Wrench, 
  Server, 
  Camera,
  X
} from 'lucide-react';
import { useI18n } from '../../shared/i18n/I18nContext';
import { SpatialAsset } from '../../shared/types';
import { SPATIAL_ASSETS_REGISTRY, SPATIAL_ASSET_CATEGORIES } from '../spatial_assets/asset_catalog';

interface SpatialCatalogDrawerProps {
  spawnedProps: string[];
  onSpawnAsset: (asset: SpatialAsset) => void;
  onClearAll: () => void;
}

export const SpatialCatalogDrawer: React.FC<SpatialCatalogDrawerProps> = ({
  spawnedProps,
  onSpawnAsset,
  onClearAll
}) => {
  const { t } = useI18n();
  const [isOpen, setIsOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const filteredAssets = selectedCategory === 'all'
    ? SPATIAL_ASSETS_REGISTRY
    : SPATIAL_ASSETS_REGISTRY.filter(a => a.category === selectedCategory);

  const getCategoryLabel = (id: string, fallback: string) => {
    const key = `catalog_${id}` as any;
    const translated = t(key);
    return translated || fallback;
  };

  return (
    <div className="absolute right-2.5 sm:right-4 8k:right-8 top-16 sm:top-24 8k:top-36 flex flex-col items-end space-y-2 8k:space-y-4 pointer-events-auto z-30">
      <div className="flex items-center space-x-2 8k:space-x-4">
        {spawnedProps.length > 0 && (
          <button
            onClick={onClearAll}
            title={t('world_clear_props')}
            aria-label={t('world_clear_props')}
            className="p-2 sm:p-2.5 8k:p-4 rounded-2xl 8k:rounded-3xl backdrop-blur-md bg-rose-950/70 border border-rose-500/40 text-rose-300 hover:bg-rose-900/80 transition-all flex items-center gap-1.5 8k:gap-3 text-xs 8k:text-lg font-semibold shadow-xl"
          >
            <Trash2 className="w-3.5 h-3.5 8k:w-6 8k:h-6" />
            <span className="hidden sm:inline">{t('world_clear_props')}</span>
            <span>({spawnedProps.length})</span>
          </button>
        )}

        <button
          onClick={() => setIsOpen(!isOpen)}
          aria-label={t('catalog_title')}
          className={`p-2.5 sm:p-3 8k:p-5 rounded-2xl 8k:rounded-3xl backdrop-blur-md border transition-all flex items-center gap-2 8k:gap-3 text-xs 8k:text-lg font-semibold shadow-xl ${
            isOpen 
              ? 'bg-cyan-500 text-slate-950 border-cyan-400 shadow-[0_0_20px_rgba(0,240,255,0.4)]' 
              : 'bg-slate-900/85 border-slate-800 text-slate-200 hover:bg-slate-800'
          }`}
        >
          <Layers className="w-4 h-4 8k:w-7 8k:h-7" />
          <span className="hidden sm:inline">{t('catalog_title')}</span>
        </button>
      </div>

      {isOpen && (
        <div className="w-[92vw] max-w-[340px] sm:max-w-[400px] 8k:max-w-[560px] max-h-[68vh] sm:max-h-[72vh] 8k:max-h-[80vh] backdrop-blur-2xl bg-slate-950/95 border border-slate-800 rounded-3xl 8k:rounded-4xl p-3.5 sm:p-5 8k:p-8 shadow-2xl flex flex-col overflow-hidden animate-fadeIn">
          <div className="flex items-center justify-between pb-3 8k:pb-5 border-b border-slate-800/80 mb-3 8k:mb-5">
            <h2 className="text-xs sm:text-sm 8k:text-xl font-bold text-slate-100 flex items-center gap-2 8k:gap-3">
              <Sparkles className="w-4 h-4 8k:w-7 8k:h-7 text-cyan-400" />
              {t('catalog_title')}
            </h2>
            <button
              onClick={() => setIsOpen(false)}
              className="text-xs 8k:text-base text-slate-400 hover:text-slate-200 p-1 rounded-lg"
              aria-label={t('close')}
            >
              <X className="w-4 h-4 8k:w-6 8k:h-6" />
            </button>
          </div>

          <div className="flex gap-1.5 8k:gap-3 overflow-x-auto pb-2 scrollbar-none mb-3 8k:mb-5">
            {SPATIAL_ASSET_CATEGORIES.map(cat => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`px-2.5 8k:px-4 py-1 8k:py-2 rounded-lg 8k:rounded-xl text-[11px] sm:text-xs 8k:text-base whitespace-nowrap transition-all ${
                  selectedCategory === cat.id 
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold' 
                    : 'bg-slate-900/80 text-slate-400 hover:text-slate-200'
                }`}
              >
                {getCategoryLabel(cat.id, cat.label)}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 8k:space-y-4 pr-1 scrollbar-thin">
            {filteredAssets.map(asset => {
              const isSpawned = spawnedProps.includes(asset.id);
              return (
                <div 
                  key={asset.id}
                  className={`p-2.5 sm:p-3 8k:p-5 rounded-2xl 8k:rounded-3xl border transition-all flex items-center justify-between gap-2.5 ${
                    isSpawned 
                      ? 'bg-cyan-950/30 border-cyan-500/40' 
                      : 'bg-slate-900/50 border-slate-800/80 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center space-x-2.5 sm:space-x-3 8k:space-x-5 overflow-hidden">
                    <div className="w-8 h-8 sm:w-9 sm:h-9 8k:w-14 8k:h-14 rounded-xl 8k:rounded-2xl bg-slate-800/80 flex items-center justify-center text-cyan-400 shrink-0">
                      {asset.id === 'prop_umbrella' && <Umbrella className="w-4 h-4 8k:w-7 8k:h-7" />}
                      {asset.id === 'tool_cad_workbench' && <Wrench className="w-4 h-4 8k:w-7 8k:h-7" />}
                      {asset.id === 'device_server_rack' && <Server className="w-4 h-4 8k:w-7 8k:h-7" />}
                      {asset.id === 'veh_surveillance_drone' && <Camera className="w-4 h-4 8k:w-7 8k:h-7" />}
                      {!['prop_umbrella', 'tool_cad_workbench', 'device_server_rack', 'veh_surveillance_drone'].includes(asset.id) && (
                        <Layers className="w-4 h-4 8k:w-7 8k:h-7" />
                      )}
                    </div>
                    <div className="overflow-hidden">
                      <div className="text-xs 8k:text-lg font-bold text-slate-200 truncate">{asset.name}</div>
                      <div className="text-[10px] sm:text-[11px] 8k:text-sm text-slate-400 truncate">{asset.description}</div>
                    </div>
                  </div>

                  <button
                    onClick={() => onSpawnAsset(asset)}
                    className={`px-2.5 sm:px-3 8k:px-5 py-1.5 8k:py-2.5 rounded-xl 8k:rounded-2xl text-xs 8k:text-base font-semibold whitespace-nowrap transition-all shrink-0 ${
                      isSpawned 
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' 
                        : 'bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400 shadow-md'
                    }`}
                  >
                    {isSpawned ? t('world_clear_props') : t('catalog_spawn_btn')}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
