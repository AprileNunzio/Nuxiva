import React, { useState } from 'react';
import { Film, Play, HardDrive, Filter } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';

interface RecordingEvent {
  id: string;
  source: string;
  time: string;
  duration: string;
  kind: 'motion' | 'ai';
  thumbnailUrl?: string;
}

const MOCK_EVENTS: RecordingEvent[] = [
  { id: 'rec_1', source: 'Ingresso Principale', time: '10:45:12', duration: '0:45', kind: 'ai' },
  { id: 'rec_2', source: 'Giardino Esterno', time: '09:20:00', duration: '1:12', kind: 'motion' },
  { id: 'rec_3', source: 'Garage', time: '08:14:30', duration: '0:30', kind: 'motion' },
];

export function View() {
  const { t } = useScopedI18n('subapps/videosorveglianza/registrazioni');
  const [filter, setFilter] = useState<'all' | 'motion' | 'ai'>('all');
  const [activeClip, setActiveClip] = useState<string | null>(null);

  const filtered = MOCK_EVENTS.filter((e) => filter === 'all' || e.kind === filter);

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-surface p-5 text-on-surface">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-outline-variant/40 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <Film className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-bold tracking-tight text-on-surface">{t('title')}</h1>
          </div>
          <p className="text-xs text-on-surface-variant">{t('subtitle')}</p>
        </div>

        <div className="flex items-center gap-2 rounded-xl bg-surface-container px-3 py-1.5 text-xs">
          <HardDrive className="h-4 w-4 text-outline" />
          <span className="text-outline">{t('storage_used')}: <strong>14.2 GB / 250 GB</strong></span>
        </div>
      </div>

      <div className="mb-4 flex items-center gap-1.5">
        <Filter className="h-3.5 w-3.5 text-outline" />
        {(['all', 'motion', 'ai'] as const).map((k) => (
          <button
            key={k}
            type="button"
            onClick={() => setFilter(k)}
            className={`rounded-full px-3 py-1 text-xs font-semibold ${
              filter === k
                ? 'bg-primary text-on-primary shadow-sm'
                : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
            }`}
          >
            {t(`filter_${k}`)}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 py-12 text-center text-outline">
          <Film className="h-10 w-10 stroke-[1.5]" />
          <p className="text-xs">{t('empty')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((item) => (
            <div
              key={item.id}
              className={`flex flex-col justify-between overflow-hidden rounded-2xl border p-3 shadow-sm transition-all ${
                activeClip === item.id
                  ? 'border-primary bg-primary-container/20 ring-1 ring-primary'
                  : 'border-outline-variant/60 bg-surface-container'
              }`}
            >
              <div className="relative aspect-video w-full rounded-xl bg-surface-container-highest flex items-center justify-center">
                <Film className="h-8 w-8 text-outline" />
                <span className="absolute bottom-2 right-2 rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] font-mono text-white">
                  {item.duration}
                </span>
              </div>
              <div className="mt-3 flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-on-surface">{item.source}</h4>
                  <span className="text-[10px] text-outline">{item.time}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveClip(item.id)}
                  className="flex items-center gap-1 rounded-xl bg-primary px-3 py-1.5 text-xs font-bold text-on-primary shadow-sm hover:opacity-90 active:scale-95"
                >
                  <Play className="h-3 w-3 fill-current" />
                  <span>{t('play')}</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default View;
