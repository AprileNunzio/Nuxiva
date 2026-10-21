import * as THREE from 'three';
import { gameState } from './gameState';
import { ChessRules } from './chessRules';
import { AiEngine } from './aiEngine';
import { ChessMove, ChessPiece, PieceColor } from './types';
import { BoardHighlights } from '../rendering/boardHighlights';
import { ShatterPhysics } from '../rendering/shatterPhysics';
import { PieceRenderer } from '../rendering/pieceRenderer';
import { MoveAnimator } from '../cinematics/moveAnimator';
import { i18n } from '../i18n/i18nService';

export class GameController {
  private scene: THREE.Scene;
  private highlights: BoardHighlights;
  private shatter: ShatterPhysics;
  private pieceRenderer: PieceRenderer;
  private animator: MoveAnimator;
  private selectedPiece: ChessPiece | null = null;
  private currentLegalMoves: ChessMove[] = [];
  private isAiThinking = false;

  constructor(
    scene: THREE.Scene,
    highlights: BoardHighlights,
    shatter: ShatterPhysics,
    pieceRenderer: PieceRenderer,
    animator: MoveAnimator
  ) {
    this.scene = scene;
    this.highlights = highlights;
    this.shatter = shatter;
    this.pieceRenderer = pieceRenderer;
    this.animator = animator;

    this.initBoardPieces();
    this.subscribeState();
  }

  private initBoardPieces(): void {
    const board = gameState.getBoard();
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        const p = board[r][c];
        if (p) {
          const mesh = this.pieceRenderer.createPieceMesh(p.type, p.color, p.id);
          if (mesh) {
            this.pieceRenderer.positionPiece(mesh, r, c);
            this.scene.add(mesh);
          }
        }
      }
    }
  }

  public handleSquareClick(row: number, col: number): void {
    if (this.animator.isBusy() || this.isAiThinking) return;
    const board = gameState.getBoard();
    const currentTurn = gameState.getTurn();
    const clickedPiece = board[row][col];

    if (this.selectedPiece) {
      const targetMove = this.currentLegalMoves.find(
        (m) => m.toRow === row && m.toCol === col
      );

      if (targetMove) {
        this.executeMoveWithAnimation(targetMove);
        this.clearSelection();
        return;
      }

      if (clickedPiece && clickedPiece.color === currentTurn) {
        this.selectPiece(clickedPiece);
        return;
      }

      this.clearSelection();
      return;
    }

    if (clickedPiece && clickedPiece.color === currentTurn) {
      this.selectPiece(clickedPiece);
    }
  }

  private selectPiece(piece: ChessPiece): void {
    this.selectedPiece = piece;
    this.highlights.setSelection(piece.row, piece.col);
    const allLegal = ChessRules.getLegalMoves(
      gameState.getBoard(),
      gameState.getTurn(),
      gameState.getLastMove()
    );
    this.currentLegalMoves = allLegal.filter(
      (m) => m.fromRow === piece.row && m.fromCol === piece.col
    );
    this.highlights.showValidMoves(this.currentLegalMoves);
  }

  private clearSelection(): void {
    this.selectedPiece = null;
    this.currentLegalMoves = [];
    this.highlights.clearSelection();
    this.highlights.clearMoves();
  }

  private executeMoveWithAnimation(move: ChessMove): void {
    const mesh = this.pieceRenderer.getMesh(move.piece.id);
    if (!mesh) return;

    this.animator.animateMove(mesh, move, () => {
      if (move.captured) {
        const capMesh = this.pieceRenderer.getMesh(move.captured.id);
        if (capMesh) {
          const capPos = capMesh.position.clone();
          this.pieceRenderer.removeMesh(move.captured.id, this.scene);
          this.shatter.spawnShatter(capPos, move.captured.color);
        }
      }
      gameState.executeMove(move);
      this.checkEndGame();
      this.triggerAiIfNeeded();
    });
  }

  public triggerAiMove(): void {
    if (this.animator.isBusy() || this.isAiThinking) return;
    const turn = gameState.getTurn();
    const best = AiEngine.findBestMove(
      gameState.getBoard(),
      turn,
      gameState.getLastMove(),
      2
    );
    if (best) {
      this.executeMoveWithAnimation(best);
    }
  }

  private triggerAiIfNeeded(): void {
    const playerColor = gameState.getPlayerColor();
    const turn = gameState.getTurn();
    if (turn !== playerColor && !gameState.isGameOver()) {
      this.isAiThinking = true;
      setTimeout(() => {
        this.isAiThinking = false;
        this.triggerAiMove();
      }, 350);
    }
  }

  private checkEndGame(): void {
    if (gameState.isCheckmate()) {
      const winner = gameState.getTurn() === 'white' ? 'black' : 'white';
      const kingPos = ChessRules.findKing(gameState.getBoard(), gameState.getTurn());
      if (kingPos) {
        const kingPiece = gameState.getBoard()[kingPos.row][kingPos.col];
        if (kingPiece) {
          const kMesh = this.pieceRenderer.getMesh(kingPiece.id);
          if (kMesh) this.animator.startKingFall(kMesh);
        }
      }
      this.showCheckmateModal(winner);
    }
  }

  private showCheckmateModal(winner: PieceColor): void {
    const overlay = document.getElementById('checkmate-overlay');
    if (overlay) {
      overlay.classList.add('visible');
      const crown = document.getElementById('checkmate-crown');
      if (crown) crown.textContent = winner === 'white' ? '♔' : '♚';
      const sub = document.getElementById('checkmate-subtitle');
      if (sub) {
        const dict = i18n.getDictionary();
        sub.textContent = winner === 'white' ? dict.dialog.whiteWins : dict.dialog.blackWins;
      }
    }
  }

  public resetGame(): void {
    const board = gameState.getBoard();
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        const p = board[r][c];
        if (p) {
          this.pieceRenderer.removeMesh(p.id, this.scene);
        }
      }
    }
    gameState.resetGame();
    this.initBoardPieces();
    this.clearSelection();

    const overlay = document.getElementById('checkmate-overlay');
    if (overlay) overlay.classList.remove('visible');
  }

  private subscribeState(): void {
    gameState.subscribe((snap) => {
      const turnDot = document.getElementById('turn-dot');
      if (turnDot) {
        turnDot.classList.toggle('black', snap.turn === 'black');
      }
      const turnText = document.getElementById('turn-text');
      if (turnText) {
        const dict = i18n.getDictionary();
        const base = snap.turn === 'white' ? dict.turn.white : dict.turn.black;
        turnText.textContent = snap.isCheck ? `${base} (${dict.turn.inCheck})` : base;
      }
      const tray = document.getElementById('captured-tray');
      if (tray) {
        const wIcons = snap.capturedWhite.map(() => '⚪').join(' ');
        const bIcons = snap.capturedBlack.map(() => '⚫').join(' ');
        tray.textContent = [wIcons, bIcons].filter(Boolean).join(' | ');
      }
    });
  }
}
