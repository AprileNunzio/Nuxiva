import { useState, useEffect } from 'react';
import { i18n } from '../i18n/i18nService';
import { TranslationDictionary } from '../i18n/types';
import { LanguageSwitcher } from './LanguageSwitcher';

interface Props {
  mobileSheetOpen: boolean;
  setMobileSheetOpen: (open: boolean | ((prev: boolean) => boolean)) => void;
  playerColor: 'white' | 'black';
  onTogglePlayerColor: () => void;
  onAiMove: () => void;
  onNewGame: () => void;
  onCameraPreset: (preset: 'player' | 'top' | 'side' | 'wide') => void;
  onToggleUI: () => void;
}

export function HudTop({
  mobileSheetOpen,
  setMobileSheetOpen,
  playerColor,
  onTogglePlayerColor,
  onAiMove,
  onNewGame,
  onCameraPreset,
  onToggleUI
}: Props) {
  const [dict, setDict] = useState<TranslationDictionary>(i18n.getDictionary());

  useEffect(() => {
    return i18n.subscribe((_, newDict) => {
      setDict(newDict);
    });
  }, []);

  return (
    <div id="hud-top">
      <div className="hud-group" id="hud-left">
        <div className="brand-pill">
          <span className="brand-title">{dict.brand.title}</span>
        </div>
        <div className="status-pill" id="status-pill">
          <span className="turn-dot" id="turn-dot"></span>
          <span id="turn-text">{dict.turn.white}</span>
          <span className="mode-badge" id="mode-badge">
            {playerColor === 'white' ? dict.turn.playingAsWhite : dict.turn.playingAsBlack}
          </span>
        </div>
        <LanguageSwitcher />
      </div>

      <button
        type="button"
        className={`hud-btn mobile-controls-trigger ${mobileSheetOpen ? 'active' : ''}`}
        id="btn-mobile-controls"
        aria-expanded={mobileSheetOpen}
        aria-controls="hud-right"
        onClick={() => setMobileSheetOpen((prev) => !prev)}
      >
        {mobileSheetOpen ? dict.controls.close : dict.controls.controls}
      </button>

      <div
        className={`mobile-sheet-backdrop ${mobileSheetOpen ? 'open' : ''}`}
        onClick={(e) => {
          e.stopPropagation();
          setMobileSheetOpen(false);
        }}
        aria-hidden="true"
      ></div>

      <div
        className={`hud-group ${mobileSheetOpen ? 'mobile-sheet-open' : ''}`}
        id="hud-right"
      >
        <div
          className="mobile-sheet-handle-wrap"
          onClick={(e) => {
            e.stopPropagation();
            setMobileSheetOpen(false);
          }}
          aria-hidden="true"
        >
          <div className="mobile-sheet-handle"></div>
        </div>

        <div className="mobile-sheet-header">
          <span className="mobile-sheet-title">{dict.controls.controls}</span>
          <button
            type="button"
            className="mobile-sheet-close"
            id="btn-mobile-sheet-close"
            onClick={(e) => {
              e.stopPropagation();
              setMobileSheetOpen(false);
            }}
            aria-label={dict.controls.close}
          >
            {dict.controls.close} ✕
          </button>
        </div>

        <div className="mobile-sheet-section-label">{dict.controls.gameActions}</div>

        <button
          className="hud-btn"
          id="btn-side-toggle"
          title={playerColor === 'white' ? dict.controls.playAsBlack : dict.controls.playAsWhite}
          onClick={() => {
            onTogglePlayerColor();
            setMobileSheetOpen(false);
          }}
        >
          {playerColor === 'white' ? dict.controls.playAsBlack : dict.controls.playAsWhite}
        </button>
        <button
          className="hud-btn"
          id="btn-ai-move"
          title={dict.controls.aiMove}
          onClick={() => {
            onAiMove();
            setMobileSheetOpen(false);
          }}
        >
          {dict.controls.aiMove}
        </button>
        <button
          className="hud-btn"
          id="btn-reset"
          title={dict.controls.newGame}
          onClick={() => {
            onNewGame();
            setMobileSheetOpen(false);
          }}
        >
          {dict.controls.newGame}
        </button>

        <div className="hud-divider" aria-hidden="true"></div>
        <div className="mobile-sheet-section-label">
          <span>{dict.controls.cameraViews}</span>
          <span className="mobile-sheet-section-sub">{dict.controls.cameraFlipHint}</span>
        </div>

        <button
          className="hud-btn active"
          id="btn-cam-player"
          title={dict.controls.camPlayer}
          onClick={() => onCameraPreset('player')}
        >
          {dict.controls.camPlayer}
        </button>
        <button
          className="hud-btn"
          id="btn-cam-top"
          title={dict.controls.camOverhead}
          onClick={() => onCameraPreset('top')}
        >
          {dict.controls.camOverhead}
        </button>
        <button
          className="hud-btn"
          id="btn-cam-side"
          title={dict.controls.camSide}
          onClick={() => onCameraPreset('side')}
        >
          {dict.controls.camSide}
        </button>
        <button
          className="hud-btn"
          id="btn-cam-wide"
          title={dict.controls.camCathedral}
          onClick={() => onCameraPreset('wide')}
        >
          {dict.controls.camCathedral}
        </button>

        <div className="hud-divider" aria-hidden="true"></div>
        <div className="mobile-sheet-section-label">{dict.controls.displayAndGestures}</div>

        <button
          className="hud-btn"
          id="btn-hide-ui"
          title={dict.controls.hideUi}
          onClick={() => {
            onToggleUI();
            setMobileSheetOpen(false);
          }}
        >
          {dict.controls.hideUi}
        </button>

        <div className="mobile-sheet-hint">
          {dict.controls.touchHint}
        </div>
      </div>
    </div>
  );
}
