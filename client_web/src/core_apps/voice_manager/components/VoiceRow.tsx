import React from 'react';
import { Check, Download, ListPlus, Loader2, Play, Star, Trash2 } from 'lucide-react';
import { Btn, Pill, Row } from '../../shared/kit';
import { VoiceItem } from '../types';

interface Props {
  readonly voice: VoiceItem;
  readonly inOrder: boolean;
  readonly busy: boolean;
  readonly playing: boolean;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly onPlay: (id: string) => void;
  readonly onDownload: (id: string) => void;
  readonly onRemove: (id: string) => void;
  readonly onAdd: (id: string) => void;
  readonly onPrefer: (voice: VoiceItem) => void;
}

const TONE = { kokoro: 'purple', piper: 'cyan', online: 'amber', studio: 'emerald' } as const;

export const VoiceRow: React.FC<Props> = ({ voice, inOrder, busy, playing, t, onPlay, onDownload, onRemove, onAdd, onPrefer }) => {
  const ready = voice.installed || !voice.downloadable;
  return (
    <Row
      actions={
        <>
          {ready ? (
            <Btn tone="slate" busy={playing} onClick={() => onPlay(voice.id)} title={t('preview')}>
              <Play className="h-3.5 w-3.5" aria-hidden="true" />
              {t('preview')}
            </Btn>
          ) : voice.downloading ? (
            <Pill tone="amber">
              <Loader2 className="mr-1 inline h-3 w-3 animate-spin" aria-hidden="true" />
              {t('downloading')}
            </Pill>
          ) : (
            <Btn tone="cyan" busy={busy} onClick={() => onDownload(voice.id)}>
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
              {t('download')}
            </Btn>
          )}
          <Btn tone={voice.preferred ? 'emerald' : 'slate'} busy={busy} onClick={() => onPrefer(voice)} title={t('prefer_hint')}>
            <Star className="h-3.5 w-3.5" aria-hidden="true" />
            {t(voice.preferred ? 'preferred' : 'prefer')}
          </Btn>
          {inOrder ? (
            <Pill tone="emerald">
              <Check className="mr-1 inline h-3 w-3" aria-hidden="true" />
              {t('in_order')}
            </Pill>
          ) : (
            <Btn tone="slate" busy={busy} onClick={() => onAdd(voice.id)} title={t('add_order')}>
              <ListPlus className="h-3.5 w-3.5" aria-hidden="true" />
            </Btn>
          )}
          {voice.engine === 'piper' && voice.installed && !inOrder ? (
            <Btn tone="rose" busy={busy} onClick={() => onRemove(voice.id)} title={t('delete')}>
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
            </Btn>
          ) : null}
        </>
      }
    >
      <div className="flex flex-wrap items-center gap-2">
        <strong className="truncate">{voice.name}</strong>
        <Pill tone={TONE[voice.engine]}>{t(`engine_${voice.engine}`)}</Pill>
        {voice.gender ? <Pill>{t(voice.gender === 'm' ? 'male' : 'female')}</Pill> : null}
        <span className="text-xs text-slate-500">
          {voice.locale}
          {voice.quality ? ` · ${voice.quality}` : ''}
          {voice.sizeMb ? ` · ${voice.sizeMb} MB` : ''}
        </span>
      </div>
    </Row>
  );
};
