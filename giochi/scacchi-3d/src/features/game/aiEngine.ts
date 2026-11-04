import { BoardMatrix, ChessMove, PieceColor, PieceType } from './types';
import { ChessRules } from './chessRules';
import { PIECE_VALUES } from './constants';

const PST_PAWN = [
  0,  0,  0,  0,  0,  0,  0,  0,
  50, 50, 50, 50, 50, 50, 50, 50,
  10, 10, 20, 30, 30, 20, 10, 10,
   5,  5, 10, 25, 25, 10,  5,  5,
   0,  0,  0, 20, 20,  0,  0,  0,
   5, -5,-10,  0,  0,-10, -5,  5,
   5, 10, 10,-20,-20, 10, 10,  5,
   0,  0,  0,  0,  0,  0,  0,  0
];

const PST_KNIGHT = [
  -50,-40,-30,-30,-30,-30,-40,-50,
  -40,-20,  0,  0,  0,  0,-20,-40,
  -30,  0, 10, 15, 15, 10,  0,-30,
  -30,  5, 15, 20, 20, 15,  5,-30,
  -30,  0, 15, 20, 20, 15,  0,-30,
  -30,  5, 10, 15, 15, 10,  5,-30,
  -40,-20,  0,  5,  5,  0,-20,-40,
  -50,-40,-30,-30,-30,-30,-40,-50
];

const PST_BISHOP = [
  -20,-10,-10,-10,-10,-10,-10,-20,
  -10,  0,  0,  0,  0,  0,  0,-10,
  -10,  0,  5, 10, 10,  5,  0,-10,
  -10,  5,  5, 10, 10,  5,  5,-10,
  -10,  0, 10, 10, 10, 10,  0,-10,
  -10, 10, 10, 10, 10, 10, 10,-10,
  -10,  5,  0,  0,  0,  0,  5,-10,
  -20,-10,-10,-10,-10,-10,-10,-20
];

export class AiEngine {
  public static evaluateBoard(board: BoardMatrix, perspectiveColor: PieceColor): number {
    let score = 0;
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        const p = board[r][c];
        if (!p) continue;
        const val = PIECE_VALUES[p.type] || 0;
        let positional = 0;
        const squareIdx = p.color === 'white' ? r * 8 + c : (7 - r) * 8 + c;

        if (p.type === 'pawn') positional = PST_PAWN[squareIdx];
        else if (p.type === 'knight') positional = PST_KNIGHT[squareIdx];
        else if (p.type === 'bishop') positional = PST_BISHOP[squareIdx];

        const total = val + positional;
        score += p.color === 'white' ? total : -total;
      }
    }
    return perspectiveColor === 'white' ? score : -score;
  }

  public static findBestMove(
    board: BoardMatrix,
    aiColor: PieceColor,
    lastMove?: ChessMove | null,
    depth: number = 2
  ): ChessMove | null {
    const legalMoves = ChessRules.getLegalMoves(board, aiColor, lastMove);
    if (legalMoves.length === 0) return null;

    legalMoves.sort((a, b) => {
      const valA = a.captured ? PIECE_VALUES[a.captured.type] : 0;
      const valB = b.captured ? PIECE_VALUES[b.captured.type] : 0;
      return valB - valA;
    });

    let bestMove = legalMoves[0];
    let bestVal = -Infinity;
    const opponentColor: PieceColor = aiColor === 'white' ? 'black' : 'white';

    for (const move of legalMoves) {
      const nextBoard = ChessRules.applyMove(board, move);
      const val = -this.minimax(nextBoard, depth - 1, -Infinity, Infinity, opponentColor, aiColor, move);
      if (val > bestVal) {
        bestVal = val;
        bestMove = move;
      }
    }

    return bestMove;
  }

  private static minimax(
    board: BoardMatrix,
    depth: number,
    alpha: number,
    beta: number,
    turnColor: PieceColor,
    rootColor: PieceColor,
    lastMove?: ChessMove | null
  ): number {
    if (depth <= 0) {
      return this.evaluateBoard(board, turnColor);
    }

    const legalMoves = ChessRules.getLegalMoves(board, turnColor, lastMove);
    if (legalMoves.length === 0) {
      if (ChessRules.isKingInCheck(board, turnColor)) {
        return -25000 - depth;
      }
      return 0;
    }

    let maxEval = -Infinity;
    const nextTurn: PieceColor = turnColor === 'white' ? 'black' : 'white';

    for (const move of legalMoves) {
      const nextBoard = ChessRules.applyMove(board, move);
      const evaluation = -this.minimax(nextBoard, depth - 1, -beta, -alpha, nextTurn, rootColor, move);
      maxEval = Math.max(maxEval, evaluation);
      alpha = Math.max(alpha, evaluation);
      if (alpha >= beta) break;
    }

    return maxEval;
  }
}
