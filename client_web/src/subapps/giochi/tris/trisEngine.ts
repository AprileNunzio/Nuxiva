import { CellValue, GameDifficulty, WinResult } from './types';

export const WIN_COMBINATIONS: ReadonlyArray<Readonly<[number, number, number]>> = [
  [0, 1, 2],
  [3, 4, 5],
  [6, 7, 8],
  [0, 3, 6],
  [1, 4, 7],
  [2, 5, 8],
  [0, 4, 8],
  [2, 4, 6],
];

export function checkWinner(board: ReadonlyArray<CellValue>): WinResult {
  for (const [a, b, c] of WIN_COMBINATIONS) {
    const valA = board[a];
    const valB = board[b];
    const valC = board[c];
    if (valA && valA === valB && valA === valC) {
      return { winner: valA, line: [a, b, c] };
    }
  }
  return { winner: null, line: null };
}

export function isBoardFull(board: ReadonlyArray<CellValue>): boolean {
  return board.every((cell) => cell !== null);
}

export function getAvailableMoves(board: ReadonlyArray<CellValue>): number[] {
  return board
    .map((val, idx) => (val === null ? idx : null))
    .filter((idx): idx is number => idx !== null);
}

function minimax(
  currentBoard: CellValue[],
  depth: number,
  isMaximizing: boolean,
  aiSymbol: 'X' | 'O',
  humanSymbol: 'X' | 'O',
  alpha: number,
  beta: number
): number {
  const result = checkWinner(currentBoard);
  if (result.winner === aiSymbol) return 10 - depth;
  if (result.winner === humanSymbol) return depth - 10;
  if (isBoardFull(currentBoard)) return 0;

  let currentAlpha = alpha;
  let currentBeta = beta;
  const available = getAvailableMoves(currentBoard);

  if (isMaximizing) {
    let maxEval = -Infinity;
    for (const pos of available) {
      currentBoard[pos] = aiSymbol;
      const evaluation = minimax(currentBoard, depth + 1, false, aiSymbol, humanSymbol, currentAlpha, currentBeta);
      currentBoard[pos] = null;
      maxEval = Math.max(maxEval, evaluation);
      currentAlpha = Math.max(currentAlpha, evaluation);
      if (currentBeta <= currentAlpha) break;
    }
    return maxEval;
  }

  let minEval = Infinity;
  for (const pos of available) {
    currentBoard[pos] = humanSymbol;
    const evaluation = minimax(currentBoard, depth + 1, true, aiSymbol, humanSymbol, currentAlpha, currentBeta);
    currentBoard[pos] = null;
    minEval = Math.min(minEval, evaluation);
    currentBeta = Math.min(currentBeta, evaluation);
    if (currentBeta <= currentAlpha) break;
  }
  return minEval;
}

export function calculateAIMove(
  board: ReadonlyArray<CellValue>,
  aiSymbol: 'X' | 'O',
  difficulty: GameDifficulty
): number {
  const available = getAvailableMoves(board);
  if (available.length === 0) return -1;
  const humanSymbol: 'X' | 'O' = aiSymbol === 'X' ? 'O' : 'X';

  if (difficulty === 'easy') {
    const randomIdx = Math.floor(Math.random() * available.length);
    return available[randomIdx] ?? available[0] ?? -1;
  }

  if (difficulty === 'medium') {
    for (const pos of available) {
      const testBoard = [...board];
      testBoard[pos] = aiSymbol;
      if (checkWinner(testBoard).winner === aiSymbol) {
        return pos;
      }
    }
    for (const pos of available) {
      const testBoard = [...board];
      testBoard[pos] = humanSymbol;
      if (checkWinner(testBoard).winner === humanSymbol) {
        return pos;
      }
    }
    const randomIdx = Math.floor(Math.random() * available.length);
    return available[randomIdx] ?? available[0] ?? -1;
  }

  let bestScore = -Infinity;
  let bestMove = available[0] ?? -1;
  const mutableBoard = [...board];

  for (const pos of available) {
    mutableBoard[pos] = aiSymbol;
    const score = minimax(mutableBoard, 0, false, aiSymbol, humanSymbol, -Infinity, Infinity);
    mutableBoard[pos] = null;
    if (score > bestScore) {
      bestScore = score;
      bestMove = pos;
    }
  }

  return bestMove;
}
