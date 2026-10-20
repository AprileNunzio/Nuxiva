import React, { useCallback, useEffect, useRef, useState } from 'react';
import { BoardHandle } from '../hooks/useBoard';
import { sendStroke, sendText } from '../data/boardApi';
import { paintBoard } from '../render/paint';
import { BOARD_BG, Item, PAGE_H, PAGE_W } from '../render/primitives';
import { Tool, useBoardI18n } from '../scope';

interface BoardCanvasProps {
  readonly handle: BoardHandle;
  readonly tool: Tool;
  readonly color: string;
  readonly width: number;
}

type Point = readonly [number, number];
const MAX_POINTS = 3000;

export const BoardCanvas: React.FC<BoardCanvasProps> = ({ handle, tool, color, width }) => {
  const { t } = useBoardI18n();
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const drawing = useRef<Point[] | null>(null);
  const pending = useRef<Item[]>([]);
  const frame = useRef(0);
  const [size, setSize] = useState(0);
  const [draft, setDraft] = useState<{ x: number; y: number; text: string } | null>(null);
  const items = handle.view?.items;
  const strokeWidth = tool === 'eraser' ? Math.min(60, width * 3) : width;

  const repaint = useCallback(() => {
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => {
      const el = canvas.current;
      const g = el?.getContext('2d');
      if (!el || !g || size === 0) {
        return;
      }
      const live: Item[] = drawing.current
        ? [{ type: tool === 'eraser' ? 'erase' : 'stroke', points: drawing.current, color, width: strokeWidth }]
        : [];
      paintBoard(g, [...(items ?? []), ...pending.current, ...live], { scale: el.width / PAGE_W }, repaint);
    });
  }, [items, size, tool, color, strokeWidth]);

  useEffect(() => {
    const el = wrap.current;
    if (!el) {
      return;
    }
    const observer = new ResizeObserver(([entry]) => setSize(Math.round(entry.contentRect.width)));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const el = canvas.current;
    if (!el || size === 0) {
      return;
    }
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    el.width = Math.round(size * dpr);
    el.height = Math.round((size * dpr * PAGE_H) / PAGE_W);
    repaint();
  }, [size, repaint]);

  useEffect(() => {
    pending.current = [];
    repaint();
  }, [items, repaint]);

  useEffect(() => () => cancelAnimationFrame(frame.current), []);

  const toPage = (event: React.PointerEvent): Point => {
    const rect = canvas.current!.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * PAGE_W;
    const y = ((event.clientY - rect.top) / rect.height) * PAGE_H;
    return [Math.round(Math.min(PAGE_W, Math.max(0, x)) * 10) / 10, Math.round(Math.min(PAGE_H, Math.max(0, y)) * 10) / 10];
  };

  const down = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (event.button !== 0) {
      return;
    }
    const point = toPage(event);
    if (tool === 'text') {
      setDraft({ x: point[0], y: point[1], text: '' });
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    drawing.current = [point];
    repaint();
  };

  const move = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const stroke = drawing.current;
    if (!stroke || stroke.length >= MAX_POINTS) {
      return;
    }
    const point = toPage(event);
    const last = stroke[stroke.length - 1];
    if (Math.hypot(point[0] - last[0], point[1] - last[1]) >= 1.5) {
      stroke.push(point);
      repaint();
    }
  };

  const up = () => {
    const stroke = drawing.current;
    drawing.current = null;
    if (!stroke) {
      return;
    }
    const eraser = tool === 'eraser';
    pending.current = [...pending.current, { type: eraser ? 'erase' : 'stroke', points: stroke, color, width: strokeWidth }];
    repaint();
    void handle.run('stroke', () => sendStroke(stroke, color, strokeWidth, eraser), 'node_board_stroke_failed');
  };

  const commitText = () => {
    if (draft && draft.text.trim()) {
      const { x, y, text } = draft;
      void handle.run('text', () => sendText(text.trim(), x, y, color), 'node_board_text_failed');
    }
    setDraft(null);
  };

  return (
    <div
      ref={wrap}
      className="relative w-full overflow-hidden rounded-2xl border border-slate-800/80 shadow-[inset_0_0_60px_rgba(0,0,0,0.45)]"
      style={{ aspectRatio: `${PAGE_W} / ${PAGE_H}`, background: BOARD_BG }}
    >
      <canvas
        ref={canvas}
        role="img"
        aria-label={t('canvas_label')}
        onPointerDown={down}
        onPointerMove={move}
        onPointerUp={up}
        onPointerCancel={up}
        className={`absolute inset-0 h-full w-full touch-none ${tool === 'text' ? 'cursor-text' : 'cursor-crosshair'}`}
      />
      {draft && (
        <input
          autoFocus
          maxLength={200}
          aria-label={t('text_input')}
          value={draft.text}
          onChange={(event) => setDraft({ ...draft, text: event.target.value })}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              commitText();
            } else if (event.key === 'Escape') {
              setDraft(null);
            }
          }}
          onBlur={commitText}
          className="absolute rounded-md border border-cyan-400/60 bg-slate-950/80 px-2 py-1 text-sm text-slate-100 outline-none"
          style={{ left: `${(draft.x / PAGE_W) * 100}%`, top: `${(draft.y / PAGE_H) * 100}%`, color }}
        />
      )}
    </div>
  );
};
