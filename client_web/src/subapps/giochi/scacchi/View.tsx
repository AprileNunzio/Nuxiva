import React, { useState, useCallback } from 'react';
import { RotateCcw, Undo2 } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';

type PieceColor = 'w' | 'b';
type PieceType = 'p' | 'r' | 'n' | 'b' | 'q' | 'k';

interface Piece {
  color: PieceColor;
  type: PieceType;
}

type Board = (Piece | null)[][];

const INITIAL_PIECES_ROW: PieceType[] = ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'];

const PIECE_SYMBOLS: Record<PieceColor, Record<PieceType, string>> = {
  w: { k: '♔', q: '♕', r: '♖', b: '♗', n: '♘', p: '♙' },
  b: { k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟' }
};

function createInitialBoard(): Board {
  const b: Board = Array(8).fill(null).map(() => Array(8).fill(null));
  for (let c = 0; c < 8; c++) {
    b[0][c] = { color: 'b', type: INITIAL_PIECES_ROW[c] };
    b[1][c] = { color: 'b', type: 'p' };
    b[6][c] = { color: 'w', type: 'p' };
    b[7][c] = { color: 'w', type: INITIAL_PIECES_ROW[c] };
  }
  return b;
}

export function View() {
  const { t } = useScopedI18n('subapps/giochi/scacchi');
  const [board, setBoard] = useState<Board>(createInitialBoard);
  const [turn, setTurn] = useState<PieceColor>('w');
  const [selected, setSelected] = useState<{ r: number; c: number } | null>(null);
  const [history, setHistory] = useState<Board[]>([]);
  const [moveCount, setMoveCount] = useState(0);

  const handleSquareClick = useCallback((r: number, c: number) => {
    const clickedPiece = board[r][c];

    if (selected) {
      if (selected.r === r && selected.c === c) {
        setSelected(null);
        return;
      }

      const activePiece = board[selected.r][selected.c];
      if (activePiece && (!clickedPiece || clickedPiece.color !== activePiece.color)) {
        setHistory((prev) => [...prev, board.map((row) => [...row])]);
        const nextBoard = board.map((row) => [...row]);
        nextBoard[r][c] = activePiece;
        nextBoard[selected.r][selected.c] = null;
        setBoard(nextBoard);
        setSelected(null);
        setTurn((prev) => (prev === 'w' ? 'b' : 'w'));
        setMoveCount((count) => count + 1);
        return;
      }
    }

    if (clickedPiece && clickedPiece.color === turn) {
      setSelected({ r, c });
    }
  }, [board, selected, turn]);

  const undoMove = () => {
    if (history.length === 0) return;
    const last = history[history.length - 1];
    setBoard(last);
    setHistory((prev) => prev.slice(0, -1));
    setTurn((prev) => (prev === 'w' ? 'b' : 'w'));
    setSelected(null);
    setMoveCount((c) => Math.max(0, c - 1));
  };

  const restart = () => {
    setBoard(createInitialBoard());
    setTurn('w');
    setSelected(null);
    setHistory([]);
    setMoveCount(0);
  };

  return (
    <div className="flex h-full flex-col items-center justify-between overflow-y-auto bg-surface p-3 text-on-surface">
      <div className="flex w-full max-w-md items-center justify-between border-b border-outline-variant/40 pb-2">
        <h2 className="text-sm font-bold tracking-tight text-on-surface">{t('title')}</h2>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-surface-container-high px-3 py-1 text-xs font-semibold text-primary">
            {turn === 'w' ? t('turn_white') : t('turn_black')}
          </span>
          <span className="text-xs text-outline">{t('moves', { count: moveCount })}</span>
        </div>
      </div>

      <div className="flex w-full max-w-md items-center justify-center p-2">
        <div className="grid aspect-square w-full max-w-[340px] grid-cols-8 overflow-hidden rounded-2xl border-2 border-outline-variant shadow-md">
          {board.map((row, r) =>
            row.map((cell, c) => {
              const isDark = (r + c) % 2 === 1;
              const isSelected = selected?.r === r && selected?.c === c;
              return (
                <button
                  key={`${r}-${c}`}
                  type="button"
                  onClick={() => handleSquareClick(r, c)}
                  className={`flex aspect-square items-center justify-center text-2xl font-normal transition-all duration-100 ${
                    isSelected
                      ? 'bg-primary-container text-on-primary-container scale-95 shadow-inner'
                      : isDark
                      ? 'bg-surface-container-highest text-on-surface'
                      : 'bg-surface-container-low text-on-surface'
                  }`}
                >
                  {cell ? (
                    <span className={cell.color === 'w' ? 'text-primary font-bold' : 'text-on-surface'}>
                      {PIECE_SYMBOLS[cell.color][cell.type]}
                    </span>
                  ) : null}
                </button>
              );
            })
          )}
        </div>
      </div>

      <div className="flex w-full max-w-md items-center justify-between gap-2 pt-2">
        <button
          type="button"
          onClick={undoMove}
          disabled={history.length === 0}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-outline-variant bg-surface-container px-3 py-2 text-xs font-semibold text-on-surface disabled:opacity-40"
        >
          <Undo2 className="h-3.5 w-3.5" />
          <span>{t('undo')}</span>
        </button>
        <button
          type="button"
          onClick={restart}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-primary px-3 py-2 text-xs font-bold text-on-primary shadow-sm hover:opacity-90 active:scale-[0.98]"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          <span>{t('restart')}</span>
        </button>
      </div>
    </div>
  );
}

export default View;
