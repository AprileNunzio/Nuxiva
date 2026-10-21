import { TranslationDictionary } from '../types';

export const it: TranslationDictionary = {
  brand: {
    title: 'Scacchi 3D',
    loadingTitle: 'Scacchi 3D',
    loadingSubtitle: 'Evocazione Architettura e Figure Scolpite...'
  },
  turn: {
    white: 'Tocca al Bianco',
    black: 'Tocca al Nero',
    playingAsWhite: 'Giocatore: Bianco',
    playingAsBlack: 'Giocatore: Nero',
    inCheck: 'Sotto Scacco'
  },
  controls: {
    playAsBlack: 'Gioca come Nero',
    playAsWhite: 'Gioca come Bianco',
    aiMove: 'Mossa IA',
    newGame: 'Nuova Partita',
    controls: 'Comandi',
    close: 'Chiudi',
    showUi: 'Mostra UI',
    hideUi: 'Nascondi UI [H]',
    cameraViews: 'Visuali Telecamera',
    cameraFlipHint: 'Tocca la visuale attiva per invertire',
    camPlayer: 'Visuale Giocatore',
    camOverhead: 'Visuale Dall\'Alto',
    camSide: 'Visuale Laterale',
    camCathedral: 'Visuale Cattedrale',
    displayAndGestures: 'Schermo & Gesti',
    gameActions: 'Azioni di Gioco',
    touchHint: 'Tocco: Seleziona pezzo per muovere • Trascina 1 dito: Ruota • Trascina 2 dita: Panoramica • Pizzica: Zoom',
    desktopHint: 'Comandi: Clicca sul pezzo per muovere • Trascina SX: Orbita • Trascina DX: Pan • Rotellina: Zoom • WASD + R/F: Volo • H: Nascondi UI'
  },
  dialog: {
    judgment: '✦   Giudizio del Santuario   ✦',
    checkmate: 'Scacco Matto',
    whiteWins: 'Il Bianco Trionfa • Il Re Nero è Caduto',
    blackWins: 'Il Nero Trionfa • Il Re Bianco è Caduto',
    replayKingFall: 'Rivedi Caduta del Re',
    dismiss: 'Chiudi',
    errorTitle: 'Anomalia di Sistema',
    errorSubtitle: 'Si è verificato un errore inatteso nel modulo 3D.',
    retry: 'Ricarica Esperienza'
  },
  pieces: {
    pawn: 'Pedone',
    knight: 'Cavallo',
    bishop: 'Alfiere',
    rook: 'Torre',
    queen: 'Regina',
    king: 'Re'
  }
};
