import React from 'react';
import { Eye, Star, Video, Wifi } from 'lucide-react';
import { CameraSource } from '../data/camerasApi';
import { useCameraI18n } from '../scope';

interface SourceListProps {
  readonly sources: readonly CameraSource[];
  readonly selected: string | null;
  readonly onSelect: (id: string) => void;
}

export const SourceList: React.FC<SourceListProps> = ({ sources, selected, onSelect }) => {
  const { t } = useCameraI18n();
  return (
    <ul className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible" aria-label={t('sources_title')}>
      {sources.map((source) => {
        const active = source.id === selected;
        const Icon = source.kind === 'ip' ? Wifi : source.kind === 'infrared' ? Eye : Video;
        return (
          <li key={source.id} className="shrink-0 lg:shrink">
            <button
              type="button"
              onClick={() => onSelect(source.id)}
              aria-current={active ? 'true' : undefined}
              className={`flex w-56 items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 lg:w-full ${
                active ? 'border-cyan-400/60 bg-cyan-400/10' : 'border-slate-800 bg-slate-950/40 hover:border-slate-600'
              } ${source.options.hidden ? 'opacity-60' : ''}`}
            >
              <Icon className={`h-4 w-4 shrink-0 ${active ? 'text-cyan-200' : 'text-slate-400'}`} aria-hidden="true" />
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-1.5 truncate text-sm font-semibold text-slate-100">
                  {source.name}
                  {source.options.favorite && <Star className="h-3 w-3 shrink-0 fill-amber-300 text-amber-300" aria-label={t('favorite')} />}
                </span>
                <span className="block truncate text-[11px] text-slate-500">
                  {[t(`kind_${source.kind}`), source.main ? t('main_badge') : null, source.options.room || null].filter(Boolean).join(' · ')}
                </span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
};
