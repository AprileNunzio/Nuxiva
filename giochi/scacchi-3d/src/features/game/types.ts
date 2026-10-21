export type PieceType = 'pawn' | 'rook' | 'knight' | 'bishop' | 'queen' | 'king';
export const PIECE_TYPES: PieceType[] = ['pawn', 'rook', 'knight', 'bishop', 'queen', 'king'];
export type PieceColor = 'white' | 'black';

export interface ChessPiece {
  id: string;
  type: PieceType;
  color: PieceColor;
  row: number;
  col: number;
  hasMoved: boolean;
}

export interface ChessMove {
  fromRow: number;
  fromCol: number;
  toRow: number;
  toCol: number;
  piece: ChessPiece;
  captured?: ChessPiece | null;
  isEnPassant?: boolean;
  isCastling?: 'kingside' | 'queenside';
  promotionType?: PieceType;
}

export type BoardMatrix = (ChessPiece | null)[][];

export interface GameSnapshot {
  turn: PieceColor;
  playerColor: PieceColor;
  isCheck: boolean;
  isCheckmate: boolean;
  isDraw: boolean;
  capturedWhite: PieceType[];
  capturedBlack: PieceType[];
  moveHistory: ChessMove[];
}
