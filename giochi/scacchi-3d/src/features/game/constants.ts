import { PieceType } from './types';

export const BOARD_SIZE = 8;
export const BOARD_SQ_SIZE = 0.34;
export const BOARD_SURFACE_Y = 0.775;

export const PIECE_VALUES: Record<PieceType, number> = {
  pawn: 100,
  knight: 320,
  bishop: 330,
  rook: 500,
  queen: 900,
  king: 20000
};

export const INITIAL_PIECE_ORDER: PieceType[] = [
  'rook',
  'knight',
  'bishop',
  'queen',
  'king',
  'bishop',
  'knight',
  'rook'
];
