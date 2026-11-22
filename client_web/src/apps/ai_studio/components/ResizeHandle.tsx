import React, { useCallback, useEffect, useRef, useState } from 'react';

/** Larghezza persistente (localStorage) e ridimensionabile via drag/tastiera. */
export function useResizableWidth(key: string, initial: number, min: number, max: number) {
  const storageKey = `ai_studio.width.${key}`;
  const [width, setWidth] = useState<number>(() => {
    const saved = Number(localStorage.getItem(storageKey));
    return Number.isFinite(saved) && saved >= min && saved <= max ? saved : initial;
  });
  const clamp = useCallback((v: number) => Math.min(max, Math.max(min, v)), [min, max]);

  useEffect(() => {
    localStorage.setItem(storageKey, String(width));
  }, [storageKey, width]);

  return { width, setWidth: (v: number) => setWidth(clamp(v)), clamp };
}

interface HandleProps {
  width: number;
  onChange: (w: number) => void;
  /** 'right' = il pannello è a sinistra del handle; 'left' = a destra. */
  side: 'right' | 'left';
  label: string;
}

export const ResizeHandle: React.FC<HandleProps> = ({ width, onChange, side, label }) => {
  const dragging = useRef(false);

  const onPointerDown = (e: React.PointerEvent) => {
    dragging.current = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    const startX = e.clientX;
    const startW = width;
    const move = (ev: PointerEvent) => {
      if (!dragging.current) return;
      const delta = ev.clientX - startX;
      onChange(side === 'right' ? startW + delta : startW - delta);
    };
    const up = () => {
      dragging.current = false;
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    const step = e.shiftKey ? 40 : 16;
    if (e.key === 'ArrowLeft') onChange(side === 'right' ? width - step : width + step);
    if (e.key === 'ArrowRight') onChange(side === 'right' ? width + step : width - step);
  };

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      tabIndex={0}
      onPointerDown={onPointerDown}
      onKeyDown={onKeyDown}
      className="hidden md:block w-1 shrink-0 cursor-col-resize bg-transparent hover:bg-cyan-400/50 focus:bg-cyan-400/60 outline-none transition-colors touch-none"
    />
  );
};
