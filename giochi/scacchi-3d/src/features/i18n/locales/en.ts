import { TranslationDictionary } from '../types';

export const en: TranslationDictionary = {
  brand: {
    title: 'Wizard Chess',
    loadingTitle: 'Wizard Chess',
    loadingSubtitle: 'Summoning Sanctum Architecture & Sculpted Pieces...'
  },
  turn: {
    white: 'White to Move',
    black: 'Black to Move',
    playingAsWhite: 'Playing as White',
    playingAsBlack: 'Playing as Black',
    inCheck: 'In Check'
  },
  controls: {
    playAsBlack: 'Play as Black',
    playAsWhite: 'Play as White',
    aiMove: 'AI Move',
    newGame: 'New Game',
    controls: 'Controls',
    close: 'Close',
    showUi: 'Show UI',
    hideUi: 'Hide UI [H]',
    cameraViews: 'Camera Views',
    cameraFlipHint: 'Tap active view to flip',
    camPlayer: 'Player Cam',
    camOverhead: 'Overhead',
    camSide: 'Side',
    camCathedral: 'Cathedral',
    displayAndGestures: 'Display & Gestures',
    gameActions: 'Game Actions',
    touchHint: 'Touch: Tap Piece to Move • 1-Finger Drag: Orbit • 2-Finger Drag: Pan • Pinch: Zoom',
    desktopHint: 'Controls: Click Piece to Move • Left-Drag: Orbit • Right-Drag: Pan • Scroll: Zoom • WASD + R/F: Fly Cam • H: Hide UI'
  },
  dialog: {
    judgment: '✦   Sanctum Judgment   ✦',
    checkmate: 'Checkmate',
    whiteWins: 'White Triumphs • The Black King Has Fallen',
    blackWins: 'Black Triumphs • The White King Has Fallen',
    replayKingFall: 'Replay King Fall',
    dismiss: 'Dismiss',
    errorTitle: 'System Anomaly',
    errorSubtitle: 'An unexpected state occurred within the 3D runtime.',
    retry: 'Reload Session'
  },
  pieces: {
    pawn: 'Pawn',
    knight: 'Knight',
    bishop: 'Bishop',
    rook: 'Rook',
    queen: 'Queen',
    king: 'King'
  }
};
