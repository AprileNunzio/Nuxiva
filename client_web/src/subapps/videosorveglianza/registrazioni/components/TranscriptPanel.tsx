import React, { useEffect, useRef } from 'react';
import { MessageSquareText, Mic } from 'lucide-react';
import type { TranscriptTurn } from '../types';
import { clock } from '../format';

interface Props {
  turns: TranscriptTurn[];
  cursorMs: number | null;
  lang: string;
  t: (key: string, params?: Record<string, string | number>) => string;
  onSeek: (atMs: number) => void;
}

export function TranscriptPanel({ turns, cursorMs, lang, t, onSeek }: Props) {
  const active = useRef<HTMLLIElement>(null);
  const current = cursorMs === null ? -1 : turns.findIndex((turn) => cursorMs >= turn.start_ms && cursorMs < turn.end_ms + 500);

  useEffect(() => {
    active.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [current]);

  return (
    <section className="flex min-h-0 flex-col gap-2" aria-label={t('transcript')}>
      <h2 className="flex items-center gap-2 text-sm font-semibold">
        <MessageSquareText className="h-4 w-4 text-tertiary" aria-hidden />
        {t('transcript')}
      </h2>
      {turns.length === 0 ? (
        <p className="text-xs text-outline">{t('no_transcript')}</p>
      ) : (
        <ol className="flex max-h-72 flex-col gap-1 overflow-y-auto pr-1">
          {turns.map((turn, index) => (
            <li key={`${turn.start_ms}-${index}`} ref={index === current ? active : undefined}>
              <button
                type="button"
                onClick={() => onSeek(turn.start_ms)}
                aria-current={index === current}
                className={`flex w-full flex-col gap-0.5 rounded-xl px-2 py-1.5 text-left text-xs ${index === current ? 'bg-tertiary/10' : 'hover:bg-on-surface/5'}`}
              >
                <span className="flex flex-wrap items-center gap-2 text-[10px] text-outline">
                  <span className="font-mono">{clock(turn.start_ms, lang)}</span>
                  <span className="font-semibold text-on-surface-variant">
                    {turn.speaker_name || turn.speaker || t('unknown_voice')}
                  </span>
                  {turn.sources.length > 1 && (
                    <span className="flex items-center gap-0.5" title={t('agreement', { value: Math.round(turn.agreement * 100) })}>
                      <Mic className="h-3 w-3" aria-hidden />
                      {t('mics', { count: turn.sources.length })}
                    </span>
                  )}
                </span>
                <span className="text-on-surface">{turn.text}</span>
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export default TranscriptPanel;
