import React, { useCallback, useMemo, useRef } from 'react';
import type { Marker, Span } from '../types';
import { clock, markerTone } from '../format';

interface Props {
  fromMs: number;
  toMs: number;
  spans: Span[];
  markers: Marker[];
  cursorMs: number | null;
  lang: string;
  label: string;
  onSeek: (atMs: number) => void;
}

const TICKS = 6;
const MAX_DOTS = 600;

export function TimelineBar({ fromMs, toMs, spans, markers, cursorMs, lang, label, onSeek }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const width = Math.max(1, toMs - fromMs);
  const pct = useCallback((ms: number) => Math.min(100, Math.max(0, ((ms - fromMs) / width) * 100)), [fromMs, width]);

  const pick = useCallback(
    (clientX: number) => {
      const box = ref.current?.getBoundingClientRect();
      if (!box || box.width <= 0) return;
      const ratio = Math.min(1, Math.max(0, (clientX - box.left) / box.width));
      onSeek(Math.round(fromMs + ratio * width));
    },
    [fromMs, width, onSeek],
  );

  const onKey = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const base = cursorMs ?? fromMs;
    const step = event.shiftKey ? 60_000 : 10_000;
    if (event.key === 'ArrowRight') onSeek(Math.min(toMs, base + step));
    else if (event.key === 'ArrowLeft') onSeek(Math.max(fromMs, base - step));
    else if (event.key === 'Home') onSeek(fromMs);
    else if (event.key === 'End') onSeek(toMs);
    else return;
    event.preventDefault();
  };

  const ticks = useMemo(
    () => Array.from({ length: TICKS + 1 }, (_, i) => fromMs + (width * i) / TICKS),
    [fromMs, width],
  );
  const dots = markers.length > MAX_DOTS ? markers.filter((_, i) => i % Math.ceil(markers.length / MAX_DOTS) === 0) : markers;

  return (
    <div className="flex flex-col gap-1 select-none">
      <div
        ref={ref}
        role="slider"
        tabIndex={0}
        aria-label={label}
        aria-valuemin={fromMs}
        aria-valuemax={toMs}
        aria-valuenow={cursorMs ?? fromMs}
        aria-valuetext={cursorMs ? clock(cursorMs, lang) : ''}
        onKeyDown={onKey}
        onPointerDown={(e) => {
          e.currentTarget.setPointerCapture(e.pointerId);
          pick(e.clientX);
        }}
        onPointerMove={(e) => {
          if (e.buttons === 1) pick(e.clientX);
        }}
        className="relative h-14 w-full cursor-pointer touch-none rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        <div className="absolute inset-x-0 top-6 h-3 rounded-full bg-on-surface/5" />
        {spans.map((s) => (
          <div
            key={s.start_ms}
            className={`absolute top-6 h-3 rounded-full ${s.audio ? 'bg-primary/60' : 'bg-primary/35'}`}
            style={{ left: `${pct(s.start_ms)}%`, width: `${Math.max(0.3, pct(s.end_ms) - pct(s.start_ms))}%` }}
          />
        ))}
        {dots.map((m) => (
          <span
            key={`${m.id}-${m.at_ms}`}
            title={`${clock(m.at_ms, lang)} · ${m.label || m.kind}`}
            className={`absolute top-1 h-3 w-1.5 -translate-x-1/2 rounded-full ${markerTone(m.kind)}`}
            style={{ left: `${pct(m.at_ms)}%` }}
          />
        ))}
        {cursorMs !== null && cursorMs >= fromMs && cursorMs <= toMs && (
          <div className="pointer-events-none absolute inset-y-0 w-0.5 bg-on-surface" style={{ left: `${pct(cursorMs)}%` }} />
        )}
      </div>
      <div className="flex justify-between text-[10px] font-mono text-outline">
        {ticks.map((t) => (
          <span key={t}>{clock(t, lang, false)}</span>
        ))}
      </div>
    </div>
  );
}

export default TimelineBar;
