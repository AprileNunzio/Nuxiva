import { BoardMatrix, ChessMove, ChessPiece, PieceColor, PieceType } from './types';
import { BOARD_SIZE } from './constants';

export class ChessRules {
  public static createInitialBoard(): BoardMatrix {
    const board: BoardMatrix = Array.from({ length: BOARD_SIZE }, () =>
      Array.from({ length: BOARD_SIZE }, () => null)
    );

    const backrow: PieceType[] = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook'];

    for (let c = 0; c < 8; c++) {
      board[0][c] = { id: `b_${backrow[c]}_${c}`, type: backrow[c], color: 'black', row: 0, col: c, hasMoved: false };
      board[1][c] = { id: `b_pawn_${c}`, type: 'pawn', color: 'black', row: 1, col: c, hasMoved: false };
      board[6][c] = { id: `w_pawn_${c}`, type: 'pawn', color: 'white', row: 6, col: c, hasMoved: false };
      board[7][c] = { id: `w_${backrow[c]}_${c}`, type: backrow[c], color: 'white', row: 7, col: c, hasMoved: false };
    }

    return board;
  }

  public static cloneBoard(board: BoardMatrix): BoardMatrix {
    return board.map((row) =>
      row.map((sq) => (sq ? { ...sq } : null))
    );
  }

  public static isSquareOnBoard(r: number, c: number): boolean {
    return r >= 0 && r < BOARD_SIZE && c >= 0 && c < BOARD_SIZE;
  }

  public static findKing(board: BoardMatrix, color: PieceColor): { row: number; col: number } | null {
    for (let r = 0; r < BOARD_SIZE; r++) {
      for (let c = 0; c < BOARD_SIZE; c++) {
        const p = board[r][c];
        if (p && p.type === 'king' && p.color === color) {
          return { row: r, col: c };
        }
      }
    }
    return null;
  }

  public static isSquareUnderAttack(
    board: BoardMatrix,
    targetRow: number,
    targetCol: number,
    byColor: PieceColor
  ): boolean {
    const pawnDir = byColor === 'white' ? -1 : 1;
    const attackerPawnRow = targetRow - pawnDir;
    for (const dCol of [-1, 1]) {
      const c = targetCol + dCol;
      if (this.isSquareOnBoard(attackerPawnRow, c)) {
        const p = board[attackerPawnRow][c];
        if (p && p.color === byColor && p.type === 'pawn') return true;
      }
    }

    const knightOffsets = [
      [-2, -1], [-2, 1], [-1, -2], [-1, 2],
      [1, -2], [1, 2], [2, -1], [2, 1]
    ];
    for (const [dr, dc] of knightOffsets) {
      const r = targetRow + dr;
      const c = targetCol + dc;
      if (this.isSquareOnBoard(r, c)) {
        const p = board[r][c];
        if (p && p.color === byColor && p.type === 'knight') return true;
      }
    }

    const kingOffsets = [
      [-1, -1], [-1, 0], [-1, 1],
      [0, -1],           [0, 1],
      [1, -1],  [1, 0],  [1, 1]
    ];
    for (const [dr, dc] of kingOffsets) {
      const r = targetRow + dr;
      const c = targetCol + dc;
      if (this.isSquareOnBoard(r, c)) {
        const p = board[r][c];
        if (p && p.color === byColor && p.type === 'king') return true;
      }
    }

    const orthoDirs = [[-1, 0], [1, 0], [0, -1], [0, 1]];
    for (const [dr, dc] of orthoDirs) {
      let r = targetRow + dr;
      let c = targetCol + dc;
      while (this.isSquareOnBoard(r, c)) {
        const p = board[r][c];
        if (p) {
          if (p.color === byColor && (p.type === 'rook' || p.type === 'queen')) return true;
          break;
        }
        r += dr;
        c += dc;
      }
    }

    const diagDirs = [[-1, -1], [-1, 1], [1, -1], [1, 1]];
    for (const [dr, dc] of diagDirs) {
      let r = targetRow + dr;
      let c = targetCol + dc;
      while (this.isSquareOnBoard(r, c)) {
        const p = board[r][c];
        if (p) {
          if (p.color === byColor && (p.type === 'bishop' || p.type === 'queen')) return true;
          break;
        }
        r += dr;
        c += dc;
      }
    }

    return false;
  }

  public static isKingInCheck(board: BoardMatrix, color: PieceColor): boolean {
    const kingPos = this.findKing(board, color);
    if (!kingPos) return false;
    const opponentColor: PieceColor = color === 'white' ? 'black' : 'white';
    return this.isSquareUnderAttack(board, kingPos.row, kingPos.col, opponentColor);
  }

  public static getPseudoLegalMovesForPiece(
    board: BoardMatrix,
    piece: ChessPiece,
    lastMove?: ChessMove | null
  ): ChessMove[] {
    const moves: ChessMove[] = [];
    const r = piece.row;
    const c = piece.col;

    if (piece.type === 'pawn') {
      const forward = piece.color === 'white' ? -1 : 1;
      const startRow = piece.color === 'white' ? 6 : 1;
      const nextR = r + forward;

      if (this.isSquareOnBoard(nextR, c) && !board[nextR][c]) {
        moves.push({ fromRow: r, fromCol: c, toRow: nextR, toCol: c, piece });
        const doubleR = r + forward * 2;
        if (r === startRow && !board[doubleR][c]) {
          moves.push({ fromRow: r, fromCol: c, toRow: doubleR, toCol: c, piece });
        }
      }

      for (const dCol of [-1, 1]) {
        const capC = c + dCol;
        if (this.isSquareOnBoard(nextR, capC)) {
          const target = board[nextR][capC];
          if (target && target.color !== piece.color) {
            moves.push({ fromRow: r, fromCol: c, toRow: nextR, toCol: capC, piece, captured: target });
          } else if (!target && lastMove && lastMove.piece.type === 'pawn' &&
                     Math.abs(lastMove.toRow - lastMove.fromRow) === 2 &&
                     lastMove.toRow === r && lastMove.toCol === capC) {
            moves.push({
              fromRow: r,
              fromCol: c,
              toRow: nextR,
              toCol: capC,
              piece,
              captured: lastMove.piece,
              isEnPassant: true
            });
          }
        }
      }
    } else if (piece.type === 'knight') {
      const offsets = [
        [-2, -1], [-2, 1], [-1, -2], [-1, 2],
        [1, -2], [1, 2], [2, -1], [2, 1]
      ];
      for (const [dr, dc] of offsets) {
        const nr = r + dr;
        const nc = c + dc;
        if (this.isSquareOnBoard(nr, nc)) {
          const target = board[nr][nc];
          if (!target || target.color !== piece.color) {
            moves.push({ fromRow: r, fromCol: c, toRow: nr, toCol: nc, piece, captured: target });
          }
        }
      }
    } else if (piece.type === 'bishop' || piece.type === 'rook' || piece.type === 'queen') {
      const dirs: number[][] = [];
      if (piece.type === 'bishop' || piece.type === 'queen') {
        dirs.push([-1, -1], [-1, 1], [1, -1], [1, 1]);
      }
      if (piece.type === 'rook' || piece.type === 'queen') {
        dirs.push([-1, 0], [1, 0], [0, -1], [0, 1]);
      }
      for (const [dr, dc] of dirs) {
        let nr = r + dr;
        let nc = c + dc;
        while (this.isSquareOnBoard(nr, nc)) {
          const target = board[nr][nc];
          if (!target) {
            moves.push({ fromRow: r, fromCol: c, toRow: nr, toCol: nc, piece });
          } else {
            if (target.color !== piece.color) {
              moves.push({ fromRow: r, fromCol: c, toRow: nr, toCol: nc, piece, captured: target });
            }
            break;
          }
          nr += dr;
          nc += dc;
        }
      }
    } else if (piece.type === 'king') {
      const dirs = [
        [-1, -1], [-1, 0], [-1, 1],
        [0, -1],           [0, 1],
        [1, -1],  [1, 0],  [1, 1]
      ];
      for (const [dr, dc] of dirs) {
        const nr = r + dr;
        const nc = c + dc;
        if (this.isSquareOnBoard(nr, nc)) {
          const target = board[nr][nc];
          if (!target || target.color !== piece.color) {
            moves.push({ fromRow: r, fromCol: c, toRow: nr, toCol: nc, piece, captured: target });
          }
        }
      }

      if (!piece.hasMoved && !this.isKingInCheck(board, piece.color)) {
        const oppColor: PieceColor = piece.color === 'white' ? 'black' : 'white';
        const kingsideRook = board[r][7];
        if (kingsideRook && !kingsideRook.hasMoved && !board[r][5] && !board[r][6]) {
          if (!this.isSquareUnderAttack(board, r, 5, oppColor) && !this.isSquareUnderAttack(board, r, 6, oppColor)) {
            moves.push({ fromRow: r, fromCol: c, toRow: r, toCol: 6, piece, isCastling: 'kingside' });
          }
        }
        const queensideRook = board[r][0];
        if (queensideRook && !queensideRook.hasMoved && !board[r][1] && !board[r][2] && !board[r][3]) {
          if (!this.isSquareUnderAttack(board, r, 2, oppColor) && !this.isSquareUnderAttack(board, r, 3, oppColor)) {
            moves.push({ fromRow: r, fromCol: c, toRow: r, toCol: 2, piece, isCastling: 'queenside' });
          }
        }
      }
    }

    return moves;
  }

  public static applyMove(board: BoardMatrix, move: ChessMove): BoardMatrix {
    const nextBoard = this.cloneBoard(board);
    const movingPiece = { ...nextBoard[move.fromRow][move.fromCol]!, row: move.toRow, col: move.toCol, hasMoved: true };

    if (move.piece.type === 'pawn') {
      const promoRow = movingPiece.color === 'white' ? 0 : 7;
      if (move.toRow === promoRow) {
        movingPiece.type = move.promotionType || 'queen';
      }
    }

    nextBoard[move.fromRow][move.fromCol] = null;
    nextBoard[move.toRow][move.toCol] = movingPiece;

    if (move.isEnPassant && move.captured) {
      nextBoard[move.captured.row][move.captured.col] = null;
    }

    if (move.isCastling === 'kingside') {
      const rook = nextBoard[move.fromRow][7];
      if (rook) {
        nextBoard[move.fromRow][7] = null;
        nextBoard[move.fromRow][5] = { ...rook, col: 5, hasMoved: true };
      }
    } else if (move.isCastling === 'queenside') {
      const rook = nextBoard[move.fromRow][0];
      if (rook) {
        nextBoard[move.fromRow][0] = null;
        nextBoard[move.fromRow][3] = { ...rook, col: 3, hasMoved: true };
      }
    }

    return nextBoard;
  }

  public static getLegalMoves(
    board: BoardMatrix,
    color: PieceColor,
    lastMove?: ChessMove | null
  ): ChessMove[] {
    const legalMoves: ChessMove[] = [];
    for (let r = 0; r < BOARD_SIZE; r++) {
      for (let c = 0; c < BOARD_SIZE; c++) {
        const p = board[r][c];
        if (p && p.color === color) {
          const candidateMoves = this.getPseudoLegalMovesForPiece(board, p, lastMove);
          for (const move of candidateMoves) {
            const simulatedBoard = this.applyMove(board, move);
            if (!this.isKingInCheck(simulatedBoard, color)) {
              legalMoves.push(move);
            }
          }
        }
      }
    }
    return legalMoves;
  }
}
