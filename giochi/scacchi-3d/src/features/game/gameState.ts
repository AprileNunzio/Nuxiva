import { BoardMatrix, ChessMove, ChessPiece, GameSnapshot, PieceColor, PieceType } from './types';
import { ChessRules } from './chessRules';
import { audioSynthesizer } from '../audio/audioSynthesizer';

type StateListener = (snapshot: GameSnapshot) => void;

export class GameStateStore {
  private static instance: GameStateStore;
  private board: BoardMatrix;
  private turn: PieceColor = 'white';
  private playerColor: PieceColor = 'white';
  private moveHistory: ChessMove[] = [];
  private capturedWhite: PieceType[] = [];
  private capturedBlack: PieceType[] = [];
  private listeners: Set<StateListener> = new Set();

  private constructor() {
    this.board = ChessRules.createInitialBoard();
  }

  public static getInstance(): GameStateStore {
    if (!GameStateStore.instance) {
      GameStateStore.instance = new GameStateStore();
    }
    return GameStateStore.instance;
  }

  public getBoard(): BoardMatrix {
    return this.board;
  }

  public getTurn(): PieceColor {
    return this.turn;
  }

  public getPlayerColor(): PieceColor {
    return this.playerColor;
  }

  public setPlayerColor(color: PieceColor): void {
    this.playerColor = color;
    this.notify();
  }

  public resetGame(): void {
    this.board = ChessRules.createInitialBoard();
    this.turn = 'white';
    this.moveHistory = [];
    this.capturedWhite = [];
    this.capturedBlack = [];
    this.notify();
  }

  public executeMove(move: ChessMove): boolean {
    const isCheck = ChessRules.isKingInCheck(this.board, this.turn);
    const legalMoves = ChessRules.getLegalMoves(this.board, this.turn, this.getLastMove());
    const isLegal = legalMoves.some(
      (m) =>
        m.fromRow === move.fromRow &&
        m.fromCol === move.fromCol &&
        m.toRow === move.toRow &&
        m.toCol === move.toCol
    );

    if (!isLegal) return false;

    if (move.captured) {
      if (move.captured.color === 'white') {
        this.capturedWhite.push(move.captured.type);
      } else {
        this.capturedBlack.push(move.captured.type);
      }
      audioSynthesizer.playCapture();
      audioSynthesizer.playShatter();
    } else {
      audioSynthesizer.playMove();
    }

    this.board = ChessRules.applyMove(this.board, move);
    this.moveHistory.push(move);
    this.turn = this.turn === 'white' ? 'black' : 'white';

    const oppCheckmate = this.isGameOver();
    if (oppCheckmate) {
      audioSynthesizer.playVictory();
    }

    this.notify();
    return true;
  }

  public getLastMove(): ChessMove | null {
    return this.moveHistory.length > 0 ? this.moveHistory[this.moveHistory.length - 1] : null;
  }

  public isCheck(): boolean {
    return ChessRules.isKingInCheck(this.board, this.turn);
  }

  public isGameOver(): boolean {
    const legalMoves = ChessRules.getLegalMoves(this.board, this.turn, this.getLastMove());
    return legalMoves.length === 0;
  }

  public isCheckmate(): boolean {
    return this.isGameOver() && this.isCheck();
  }

  public isDraw(): boolean {
    return this.isGameOver() && !this.isCheck();
  }

  public getSnapshot(): GameSnapshot {
    return {
      turn: this.turn,
      playerColor: this.playerColor,
      isCheck: this.isCheck(),
      isCheckmate: this.isCheckmate(),
      isDraw: this.isDraw(),
      capturedWhite: [...this.capturedWhite],
      capturedBlack: [...this.capturedBlack],
      moveHistory: [...this.moveHistory]
    };
  }

  public subscribe(listener: StateListener): () => void {
    this.listeners.add(listener);
    listener(this.getSnapshot());
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notify(): void {
    const snapshot = this.getSnapshot();
    for (const listener of this.listeners) {
      listener(snapshot);
    }
  }
}

export const gameState = GameStateStore.getInstance();
