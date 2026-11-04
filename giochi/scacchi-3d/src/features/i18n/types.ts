export type SupportedLocale = 'it' | 'en';

export interface TranslationDictionary {
  brand: {
    title: string;
    loadingTitle: string;
    loadingSubtitle: string;
  };
  turn: {
    white: string;
    black: string;
    playingAsWhite: string;
    playingAsBlack: string;
    inCheck: string;
  };
  controls: {
    playAsBlack: string;
    playAsWhite: string;
    aiMove: string;
    newGame: string;
    controls: string;
    close: string;
    showUi: string;
    hideUi: string;
    cameraViews: string;
    cameraFlipHint: string;
    camPlayer: string;
    camOverhead: string;
    camSide: string;
    camCathedral: string;
    displayAndGestures: string;
    gameActions: string;
    touchHint: string;
    desktopHint: string;
  };
  dialog: {
    judgment: string;
    checkmate: string;
    whiteWins: string;
    blackWins: string;
    replayKingFall: string;
    dismiss: string;
    errorTitle: string;
    errorSubtitle: string;
    retry: string;
  };
  pieces: {
    pawn: string;
    knight: string;
    bishop: string;
    rook: string;
    queen: string;
    king: string;
  };
}
