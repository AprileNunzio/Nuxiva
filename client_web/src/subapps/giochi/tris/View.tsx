import React, { useState, useCallback, useEffect } from 'react';
import { RotateCcw, User, Bot } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';

type CellValue = 'X' | 'O' | null;

const WIN_COMBINATIONS = [
  [0, 1, 2], [3, 4, 5], [6, 7, 8],
  [0, 3, 6], [1, 4, 7], [2, 5, 8],
  [0, 4, 8], [2, 4, 6]
];

export function View() {
  const { t } = useScopedI18n('subapps/giochi/tris');
  const [board, setBoard] = useState<CellValue[]>(Array(9).fill(null));
  const [turn, setTurn] = useState<'X' | 'O'>('X');
  const [mode, setMode] = useState<'pvp' | 'ai'>('ai');
  const [scores, setScores] = useState({ x: 0, o: 0, tie: 0 });

  const checkWinner = useCallback((currentBoard: CellValue[]): { winner: 'X' | 'O' | null; line: number[] | null } => {
    for (const line of WIN_COMBINATIONS) {
      const [a, b, c] = line;
      if (currentBoard[a] && currentBoard[a] === currentBoard[b] && currentBoard[a] === currentBoard[c]) {
        return { winner: currentBoard[a], line };
      }
    }
    return { winner: null, line: null };
  }, []);

  const winResult = checkWinner(board);
  const isFull = board.every((cell) => cell !== null);
  const isGameOver = winResult.winner !== null || isFull;

  const handleCellClick = useCallback((index: number) => {
    if (board[index] || isGameOver) return;

    const nextBoard = [...board];
    nextBoard[index] = turn;
    setBoard(nextBoard);

    const res = checkWinner(nextBoard);
    if (res.winner) {
      setScores((s) => ({ ...s, [res.winner === 'X' ? 'x' : 'o']: s[res.winner === 'X' ? 'x' : 'o'] + 1 }));
    } else if (nextBoard.every((cell) => cell !== null)) {
      setScores((s) => ({ ...s, tie: s.tie + 1 }));
    } else {
      setTurn(turn === 'X' ? 'O' : 'X');
    }
  }, [board, isGameOver, turn, checkWinner]);

  useEffect(() => {
    if (mode === 'ai' && turn === 'O' && !isGameOver) {
      const timer = window.setTimeout(() => {
        const emptyIndices = board
          .map((v, i) => (v === null ? i : null))
          .filter((v): v is number => v !== null);

        if (emptyIndices.length === 0) return;

        let selected = emptyIndices[0];
        for (const idx of emptyIndices) {
          const test = [...board];
          test[idx] = 'O';
          if (checkWinner(test).winner === 'O') {
            selected = idx;
            break;
          }
        }

        if (selected === emptyIndices[0]) {
          for (const idx of emptyIndices) {
            const test = [...board];
            test[idx] = 'X';
            if (checkWinner(test).winner === 'X') {
              selected = idx;
              break;
            }
          }
        }

        handleCellClick(selected);
      }, 350);

      return () => window.clearTimeout(timer);
    }
  }, [mode, turn, isGameOver, board, checkWinner, handleCellClick]);

  const restart = () => {
    setBoard(Array(9).fill(null));
    setTurn('X');
  };

  return (
    <div className="flex h-full flex-col items-center justify-between overflow-y-auto bg-surface p-4 text-on-surface">
      <div className="flex w-full max-w-sm items-center justify-between gap-2 border-b border-outline-variant/40 pb-3">
        <h2 className="text-base font-bold tracking-tight text-on-surface">{t('title')}</h2>
        <div className="flex items-center gap-1 rounded-full bg-surface-container-high p-1">
          <button
            type="button"
            onClick={() => { setMode('pvp'); restart(); }}
            className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${mode === 'pvp' ? 'bg-primary text-on-primary shadow-sm' : 'text-on-surface-variant'}`}
          >
            <User className="h-3 w-3" />
            <span>{t('mode_pvp')}</span>
          </button>
          <button
            type="button"
            onClick={() => { setMode('ai'); restart(); }}
            className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${mode === 'ai' ? 'bg-primary text-on-primary shadow-sm' : 'text-on-surface-variant'}`}
          >
            <Bot className="h-3 w-3" />
            <span>{t('mode_ai')}</span>
          </button>
        </div>
      </div>

      <div className="my-2 flex w-full max-w-sm justify-around rounded-xl bg-surface-container px-3 py-2 text-center text-xs">
        <div>
          <span className="block font-semibold text-primary">{t('score_x')}</span>
          <strong className="text-lg">{scores.x}</strong>
        </div>
        <div>
          <span className="block text-outline">{t('score_tie')}</span>
          <strong className="text-lg">{scores.tie}</strong>
        </div>
        <div>
          <span className="block font-semibold text-secondary">{t('score_o')}</span>
          <strong className="text-lg">{scores.o}</strong>
        </div>
      </div>

      <div className="flex items-center justify-center py-1">
        <span className="text-xs font-medium text-on-surface-variant">
          {winResult.winner
            ? t('winner', { player: winResult.winner })
            : isFull
            ? t('tie')
            : turn === 'X'
            ? t('turn_x')
            : t('turn_o')}
        </span>
      </div>

      <div className="grid aspect-square w-full max-w-[280px] grid-cols-3 gap-2 p-2">
        {board.map((cell, idx) => {
          const isWinning = winResult.line?.includes(idx);
          return (
            <button
              key={idx}
              type="button"
              disabled={isGameOver || cell !== null}
              onClick={() => handleCellClick(idx)}
              className={`flex aspect-square items-center justify-center rounded-2xl border text-3xl font-extrabold transition-all duration-150 ${
                isWinning
                  ? 'border-primary bg-primary-container text-on-primary-container scale-105 shadow-md'
                  : cell
                  ? 'border-outline-variant bg-surface-container-high text-on-surface'
                  : 'border-outline-variant/60 bg-surface-container hover:border-primary/50 hover:bg-surface-container-highest'
              }`}
            >
              {cell === 'X' ? (
                <span className="text-primary">X</span>
              ) : cell === 'O' ? (
                <span className="text-secondary">O</span>
              ) : null}
            </button>
          );
        })}
      </div>

      <div className="w-full max-w-sm pt-2">
        <button
          type="button"
          onClick={restart}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-on-primary shadow-sm hover:opacity-90 active:scale-[0.98]"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          <span>{t('restart')}</span>
        </button>
      </div>
    </div>
  );
}

export default View;
