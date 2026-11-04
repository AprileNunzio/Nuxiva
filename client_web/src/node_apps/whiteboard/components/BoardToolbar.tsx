import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, Eraser, FilePlus2, Pen, Sparkles, Trash2, Type, Undo2, X } from 'lucide-react';
import { ConfirmDialog } from '../../../shared/ui/ConfirmDialog';
import { clearBoard, deletePage, newPage, setAi, switchPage, undo } from '../data/boardApi';
import { BoardHandle } from '../hooks/useBoard';
import { INKS, WIDTHS } from '../render/primitives';
import { Tool, useBoardI18n } from '../scope';

interface BoardToolbarProps {
  readonly handle: BoardHandle;
  readonly tool: Tool;
  readonly color: string;
  readonly width: number;
  readonly onTool: (tool: Tool) => void;
  readonly onColor: (color: string) => void;
  readonly onWidth: (width: number) => void;
}

const button =
  'flex h-9 min-w-9 items-center justify-center gap-1.5 rounded-lg border px-2 text-xs font-semibold transition disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400';
const idle = 'border-slate-700 text-slate-300 hover:border-cyan-400/50 hover:text-white';
const active = 'border-cyan-400/70 bg-cyan-400/15 text-cyan-100';

export const BoardToolbar: React.FC<BoardToolbarProps> = ({ handle, tool, color, width, onTool, onColor, onWidth }) => {
  const { t } = useBoardI18n();
  const [confirm, setConfirm] = useState<'clear' | 'page' | null>(null);
  const view = handle.view;
  const page = view?.page ?? 0;
  const pages = view?.pages ?? 1;
  const busy = handle.busy !== null;
  const tools: readonly (readonly [Tool, React.ReactNode])[] = [
    ['pen', <Pen key="pen" className="h-4 w-4" aria-hidden="true" />],
    ['eraser', <Eraser key="eraser" className="h-4 w-4" aria-hidden="true" />],
    ['text', <Type key="text" className="h-4 w-4" aria-hidden="true" />],
  ];

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-slate-800/80 bg-slate-950/60 p-2">
      <div className="flex gap-1" role="radiogroup" aria-label={t('tools')}>
        {tools.map(([key, icon]) => (
          <button key={key} type="button" role="radio" aria-checked={tool === key} aria-label={t(`tool_${key}`)} onClick={() => onTool(key)} className={`${button} ${tool === key ? active : idle}`}>
            {icon}
          </button>
        ))}
      </div>
      <span className="h-6 w-px bg-slate-800" aria-hidden="true" />
      <div className="flex gap-1" role="radiogroup" aria-label={t('colors')}>
        {INKS.map((ink) => (
          <button
            key={ink}
            type="button"
            role="radio"
            aria-checked={color === ink}
            aria-label={ink}
            onClick={() => onColor(ink)}
            className={`h-7 w-7 rounded-full border-2 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${color === ink ? 'scale-110 border-white' : 'border-transparent'}`}
            style={{ background: ink }}
          />
        ))}
      </div>
      <div className="flex gap-1" role="radiogroup" aria-label={t('widths')}>
        {Object.entries(WIDTHS).map(([key, value]) => (
          <button key={key} type="button" role="radio" aria-checked={width === value} aria-label={t(`width_${key}`)} onClick={() => onWidth(value)} className={`${button} ${width === value ? active : idle}`}>
            <span className="rounded-full bg-current" style={{ width: value / 1.5 + 2, height: value / 1.5 + 2 }} />
          </button>
        ))}
      </div>
      <span className="h-6 w-px bg-slate-800" aria-hidden="true" />
      <button type="button" disabled={busy} aria-label={t('undo')} onClick={() => void handle.run('undo', undo, 'node_board_action_failed')} className={`${button} ${idle}`}>
        <Undo2 className="h-4 w-4" aria-hidden="true" />
      </button>
      <button type="button" disabled={busy} aria-label={t('clear')} onClick={() => setConfirm('clear')} className={`${button} ${idle} hover:border-rose-400/60`}>
        <Trash2 className="h-4 w-4" aria-hidden="true" />
      </button>
      <span className="h-6 w-px bg-slate-800" aria-hidden="true" />
      <div className="flex items-center gap-1">
        <button type="button" disabled={busy || page === 0} aria-label={t('page_prev')} onClick={() => void handle.run('page', () => switchPage(page - 1), 'node_board_action_failed')} className={`${button} ${idle}`}>
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        </button>
        <span className="min-w-14 text-center font-mono text-xs text-slate-300">{t('page_of', { page: page + 1, pages })}</span>
        <button type="button" disabled={busy || page >= pages - 1} aria-label={t('page_next')} onClick={() => void handle.run('page', () => switchPage(page + 1), 'node_board_action_failed')} className={`${button} ${idle}`}>
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </button>
        <button type="button" disabled={busy} aria-label={t('page_new')} onClick={() => void handle.run('page', newPage, 'node_board_action_failed')} className={`${button} ${idle}`}>
          <FilePlus2 className="h-4 w-4" aria-hidden="true" />
        </button>
        {pages > 1 && (
          <button type="button" disabled={busy} aria-label={t('page_delete')} onClick={() => setConfirm('page')} className={`${button} ${idle} hover:border-rose-400/60`}>
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        )}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={view?.aiEnabled ?? false}
        disabled={busy || !view}
        onClick={() => void handle.run('ai', () => setAi(!(view?.aiEnabled ?? true)), 'node_board_action_failed')}
        className={`${button} ml-auto ${view?.aiEnabled ? 'border-indigo-400/60 bg-indigo-400/15 text-indigo-100' : idle}`}
      >
        <Sparkles className="h-4 w-4" aria-hidden="true" />
        {t(view?.aiEnabled ? 'ai_on' : 'ai_off')}
      </button>
      {confirm && (
        <ConfirmDialog
          title={t(confirm === 'clear' ? 'clear_title' : 'page_delete_title')}
          body={t(confirm === 'clear' ? 'clear_body' : 'page_delete_body', { page: page + 1 })}
          confirmLabel={t(confirm === 'clear' ? 'clear' : 'page_delete')}
          cancelLabel={t('cancel')}
          pending={busy}
          tone="danger"
          onConfirm={() =>
            void handle
              .run(confirm, confirm === 'clear' ? clearBoard : () => deletePage(page), 'node_board_action_failed')
              .then(() => setConfirm(null))
          }
          onCancel={() => setConfirm(null)}
        />
      )}
    </div>
  );
};
