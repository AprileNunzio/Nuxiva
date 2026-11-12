import React, { useState, useCallback, useEffect, useRef } from 'react';
import { RotateCcw, User, Bot, Mic, MicOff, Save, FolderOpen, Trash2, X } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { CellValue, GameMode, GameDifficulty, SavedGame } from './types';
import { checkWinner, isBoardFull, calculateAIMove } from './trisEngine';
import { parseVoiceMove, speakFeedback, createSpeechRecognizer } from './voiceEngine';
import { getSavedGames, saveGame, deleteSavedGame, loadScores, saveScores } from './storage';

export function View() {
  const { t, lang } = useScopedI18n('subapps/giochi/tris');
  const [board, setBoard] = useState<CellValue[]>(Array(9).fill(null));
  const [turn, setTurn] = useState<'X' | 'O'>('X');
  const [mode, setMode] = useState<GameMode>('ai');
  const [difficulty, setDifficulty] = useState<GameDifficulty>('hard');
  const [scores, setScores] = useState(loadScores);
  const [isListening, setIsListening] = useState(false);
  const [voiceNotice, setVoiceNotice] = useState<string>('');
  const [showSavesModal, setShowSavesModal] = useState(false);
  const [savedGamesList, setSavedGamesList] = useState<SavedGame[]>([]);

  const recognizerRef = useRef<{ start: () => void; stop: () => void } | null>(null);

  const winResult = checkWinner(board);
  const isFull = isBoardFull(board);
  const isGameOver = winResult.winner !== null || isFull;

  const handleCellClick = useCallback((index: number) => {
    if (board[index] || isGameOver) return;

    const nextBoard = [...board];
    nextBoard[index] = turn;
    setBoard(nextBoard);

    const res = checkWinner(nextBoard);
    if (res.winner) {
      setScores((s) => {
        const nextScores = { ...s, [res.winner === 'X' ? 'x' : 'o']: s[res.winner === 'X' ? 'x' : 'o'] + 1 };
        saveScores(nextScores);
        return nextScores;
      });
      speakFeedback(t('winner_speech', { player: res.winner }), lang);
    } else if (isBoardFull(nextBoard)) {
      setScores((s) => {
        const nextScores = { ...s, tie: s.tie + 1 };
        saveScores(nextScores);
        return nextScores;
      });
      speakFeedback(t('tie_speech'), lang);
    } else {
      setTurn(turn === 'X' ? 'O' : 'X');
    }
  }, [board, isGameOver, turn, t, lang]);

  useEffect(() => {
    if (mode === 'ai' && turn === 'O' && !isGameOver) {
      const timer = window.setTimeout(() => {
        const aiPos = calculateAIMove(board, 'O', difficulty);
        if (aiPos >= 0) {
          handleCellClick(aiPos);
          speakFeedback(t('ai_moved_speech', { pos: aiPos + 1 }), lang);
        }
      }, 400);

      return () => window.clearTimeout(timer);
    }
  }, [mode, turn, isGameOver, board, difficulty, handleCellClick, t, lang]);

  useEffect(() => {
    if (!isListening) {
      recognizerRef.current?.stop();
      return;
    }

    const rec = createSpeechRecognizer(
      lang.startsWith('en') ? 'en-US' : 'it-IT',
      (transcript) => {
        setVoiceNotice(transcript);
        const pos = parseVoiceMove(transcript);
        if (pos !== null && !board[pos] && !isGameOver) {
          handleCellClick(pos);
        }
      },
      () => setIsListening(false),
      () => setIsListening(false)
    );

    if (rec) {
      recognizerRef.current = rec;
      rec.start();
    } else {
      setIsListening(false);
    }

    return () => {
      rec?.stop();
    };
  }, [isListening, board, isGameOver, handleCellClick, lang]);

  const restart = () => {
    setBoard(Array(9).fill(null));
    setTurn('X');
    setVoiceNotice('');
  };

  const handleSaveCurrent = () => {
    const item: SavedGame = {
      id: `save_${Date.now()}`,
      name: `${t('title')} - ${new Date().toLocaleTimeString()}`,
      timestamp: Date.now(),
      board,
      turn,
      mode,
      difficulty,
      scores,
    };
    saveGame(item);
    setSavedGamesList(getSavedGames());
    setVoiceNotice(t('game_saved'));
  };

  const handleOpenSaves = () => {
    setSavedGamesList(getSavedGames());
    setShowSavesModal(true);
  };

  const handleResume = (item: SavedGame) => {
    setBoard(item.board);
    setTurn(item.turn);
    setMode(item.mode);
    setDifficulty(item.difficulty);
    setScores(item.scores);
    setShowSavesModal(false);
    setVoiceNotice(t('game_resumed'));
  };

  const handleDeleteSave = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    deleteSavedGame(id);
    setSavedGamesList(getSavedGames());
  };

  return (
    <div className="flex h-full flex-col items-center justify-between overflow-y-auto bg-surface p-3 text-on-surface sm:p-5">
      <div className="flex w-full max-w-md items-center justify-between gap-2 border-b border-outline-variant/40 pb-3">
        <h2 className="text-base font-bold tracking-tight text-on-surface">{t('title')}</h2>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setIsListening(!isListening)}
            title={t('voice_mic_tooltip')}
            className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold transition-all ${
              isListening ? 'bg-error text-on-error animate-pulse' : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
            }`}
          >
            {isListening ? <Mic className="h-3.5 w-3.5" /> : <MicOff className="h-3.5 w-3.5" />}
            <span className="hidden sm:inline">{isListening ? t('listening') : t('voice')}</span>
          </button>
          <div className="flex items-center rounded-full bg-surface-container-high p-0.5">
            <button
              type="button"
              onClick={() => { setMode('pvp'); restart(); }}
              className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${mode === 'pvp' ? 'bg-primary text-on-primary' : 'text-on-surface-variant'}`}
            >
              <User className="h-3 w-3" />
              <span className="hidden sm:inline">{t('mode_pvp')}</span>
            </button>
            <button
              type="button"
              onClick={() => { setMode('ai'); restart(); }}
              className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${mode === 'ai' ? 'bg-primary text-on-primary' : 'text-on-surface-variant'}`}
            >
              <Bot className="h-3 w-3" />
              <span className="hidden sm:inline">{t('mode_ai')}</span>
            </button>
          </div>
        </div>
      </div>

      {mode === 'ai' && (
        <div className="mt-2 flex items-center gap-2 text-xs">
          <span className="text-on-surface-variant font-medium">{t('difficulty')}:</span>
          {(['easy', 'medium', 'hard'] as const).map((diff) => (
            <button
              key={diff}
              type="button"
              onClick={() => { setDifficulty(diff); restart(); }}
              className={`rounded-md px-2 py-0.5 font-semibold capitalize ${difficulty === diff ? 'bg-secondary text-on-secondary' : 'bg-surface-container text-on-surface-variant'}`}
            >
              {t(`diff_${diff}`)}
            </button>
          ))}
        </div>
      )}

      {voiceNotice && (
        <div className="my-1 text-center text-xs font-medium text-primary">
          {voiceNotice}
        </div>
      )}

      <div className="my-2 flex w-full max-w-md justify-around rounded-xl bg-surface-container px-3 py-2 text-center text-xs">
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

      <div className="grid aspect-square w-full max-w-[280px] grid-cols-3 gap-2 p-1">
        {board.map((cell, idx) => {
          const isWinning = winResult.line?.includes(idx);
          return (
            <button
              key={idx}
              type="button"
              disabled={isGameOver || cell !== null}
              onClick={() => handleCellClick(idx)}
              className={`relative flex aspect-square items-center justify-center rounded-2xl border text-3xl font-black transition-all duration-150 ${
                isWinning
                  ? 'border-primary bg-primary-container text-on-primary-container scale-105 shadow-md'
                  : cell
                  ? 'border-outline-variant bg-surface-container-high text-on-surface'
                  : 'border-outline-variant/60 bg-surface-container hover:border-primary/50 hover:bg-surface-container-highest'
              }`}
            >
              <span className="absolute top-1 left-2 text-[9px] font-medium text-outline-variant">{idx + 1}</span>
              {cell === 'X' ? (
                <span className="text-primary">X</span>
              ) : cell === 'O' ? (
                <span className="text-secondary">O</span>
              ) : null}
            </button>
          );
        })}
      </div>

      <div className="mt-2 flex w-full max-w-md items-center gap-2">
        <button
          type="button"
          onClick={restart}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-primary px-3 py-2 text-xs font-bold text-on-primary shadow-sm hover:opacity-90 active:scale-[0.98]"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          <span>{t('restart')}</span>
        </button>
        <button
          type="button"
          onClick={handleSaveCurrent}
          title={t('save_game')}
          className="flex items-center gap-1 rounded-xl bg-surface-container-high px-3 py-2 text-xs font-semibold text-on-surface hover:bg-surface-container-highest active:scale-[0.98]"
        >
          <Save className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">{t('save')}</span>
        </button>
        <button
          type="button"
          onClick={handleOpenSaves}
          title={t('load_game')}
          className="flex items-center gap-1 rounded-xl bg-surface-container-high px-3 py-2 text-xs font-semibold text-on-surface hover:bg-surface-container-highest active:scale-[0.98]"
        >
          <FolderOpen className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">{t('load')}</span>
        </button>
      </div>

      {showSavesModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
          <div className="flex max-h-[80vh] w-full max-w-sm flex-col rounded-2xl bg-surface-container-highest p-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-outline-variant/40 pb-2">
              <h3 className="text-sm font-bold text-on-surface">{t('saved_games_title')}</h3>
              <button type="button" onClick={() => setShowSavesModal(false)} className="rounded-lg p-1 text-on-surface-variant hover:bg-surface-container">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-3 flex-1 space-y-2 overflow-y-auto">
              {savedGamesList.length === 0 ? (
                <p className="py-6 text-center text-xs text-on-surface-variant">{t('no_saved_games')}</p>
              ) : (
                savedGamesList.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => handleResume(item)}
                    className="flex cursor-pointer items-center justify-between rounded-xl bg-surface-container p-2.5 text-xs hover:bg-surface-container-high transition-colors"
                  >
                    <div>
                      <strong className="block text-on-surface">{item.name}</strong>
                      <span className="text-[10px] text-on-surface-variant">
                        {item.mode.toUpperCase()} · {t(`diff_${item.difficulty}`)}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => handleDeleteSave(item.id, e)}
                      className="rounded-lg p-1.5 text-error hover:bg-error/10"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default View;
