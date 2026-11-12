import React, { useState } from 'react';
import { Loader2, MessageSquareText, Search, Sparkles } from 'lucide-react';
import { findRecordings } from '../api';
import type { FindHit, FindResult } from '../types';
import { clock, dayLabel } from '../format';

interface Props {
  camera: string;
  lang: string;
  t: (key: string, params?: Record<string, string | number>) => string;
  kindLabel: (kind: string) => string;
  onOpen: (camera: string, atMs: number) => void;
}

export function SearchPanel({ camera, lang, t, kindLabel, onOpen }: Props) {
  const [query, setQuery] = useState('');
  const [onlyCamera, setOnlyCamera] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<FindResult | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!query.trim() || busy) return;
    setBusy(true);
    setResult(await findRecordings(query, onlyCamera ? camera : ''));
    setBusy(false);
  };

  const cameraName = (id: string) => result?.cameras[id]?.name || id;
  const hits: FindHit[] = result ? [...result.speech, ...result.events].sort((a, b) => b.at_ms - a.at_ms) : [];

  return (
    <section className="flex flex-col gap-2" aria-label={t('search')}>
      <form onSubmit={(e) => void submit(e)} className="flex flex-wrap items-center gap-2" role="search">
        <label className="flex min-w-0 flex-1 items-center gap-2 rounded-full px-3 py-1.5 ring-1 ring-outline/30 focus-within:ring-primary">
          <Search className="h-4 w-4 shrink-0 text-outline" aria-hidden />
          <input
            type="search"
            value={query}
            maxLength={300}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('search_placeholder')}
            aria-label={t('search')}
            className="min-w-0 flex-1 bg-transparent text-xs outline-none placeholder:text-outline"
          />
          {busy && <Loader2 className="h-4 w-4 animate-spin text-outline" aria-hidden />}
        </label>
        <label className="flex items-center gap-1.5 text-xs text-on-surface-variant">
          <input type="checkbox" checked={onlyCamera} onChange={(e) => setOnlyCamera(e.target.checked)} />
          {t('search_this_camera')}
        </label>
      </form>
      {result && (
        hits.length === 0 ? (
          <p className="text-xs text-outline">{t('search_none')}</p>
        ) : (
          <ol className="flex max-h-64 flex-col gap-1 overflow-y-auto pr-1" aria-live="polite">
            <li className="text-[10px] text-outline">{t('search_count', { speech: result.speech.length, events: result.events.length })}</li>
            {hits.map((hit, index) => (
              <li key={`${hit.kind}-${hit.camera}-${hit.at_ms}-${index}`}>
                <button
                  type="button"
                  disabled={hit.kind !== 'speech' && !hit.segment}
                  onClick={() => onOpen(hit.camera, hit.kind === 'speech' ? hit.at_ms : hit.at_ms - 3000)}
                  className="flex w-full items-start gap-2 rounded-xl px-2 py-1.5 text-left text-xs hover:bg-on-surface/5 disabled:opacity-50"
                >
                  {hit.kind === 'speech' ? (
                    <MessageSquareText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-tertiary" aria-hidden />
                  ) : (
                    <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" aria-hidden />
                  )}
                  <span className="flex min-w-0 flex-col gap-0.5">
                    <span className="flex flex-wrap gap-2 text-[10px] text-outline">
                      <span className="font-mono">{dayLabel(hit.at_ms, lang)} {clock(hit.at_ms, lang)}</span>
                      <span className="font-semibold text-on-surface-variant">{cameraName(hit.camera)}</span>
                      <span>
                        {hit.kind === 'speech' ? hit.speaker_name || hit.speaker || hit.voice || t('unknown_voice') : kindLabel(hit.kind)}
                      </span>
                    </span>
                    <span className="truncate text-on-surface">{hit.text || kindLabel(hit.kind)}</span>
                  </span>
                </button>
              </li>
            ))}
          </ol>
        )
      )}
    </section>
  );
}

export default SearchPanel;
