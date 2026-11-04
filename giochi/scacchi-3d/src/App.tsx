import { useEffect, useRef, useState } from 'react';
import { initWizardChess } from './wizardChessEngine.js';
import { ErrorBoundary } from './features/errors/ErrorBoundary';
import { globalErrorHandler } from './features/errors/globalErrorHandler';
import { i18n } from './features/i18n/i18nService';
import { SupportedLocale, TranslationDictionary } from './features/i18n/types';
import { LanguageSwitcher } from './features/ui/LanguageSwitcher';

export default function App() {
  const initializedRef = useRef(false);
  const [mobileSheetOpen, setMobileSheetOpen] = useState(false);
  const [dict, setDict] = useState<TranslationDictionary>(i18n.getDictionary());
  const [playingAsWhite, setPlayingAsWhite] = useState(true);

  useEffect(() => {
    globalErrorHandler.init();
    if (initializedRef.current) return;
    initializedRef.current = true;
    initWizardChess();
  }, []);

  useEffect(() => {
    return i18n.subscribe((_: SupportedLocale, newDict: TranslationDictionary) => {
      setDict(newDict);
    });
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMobileSheetOpen(false);
      }
    };
    const handleResize = () => {
      if (window.innerWidth > 768) {
        setMobileSheetOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  const handleRestoreUI = () => {
    const win = window as unknown as { wizardChess?: { toggleUI?: (force?: boolean) => void } };
    if (win.wizardChess?.toggleUI) {
      win.wizardChess.toggleUI(false);
    } else {
      document.body.classList.remove('cinematic-ui-hidden');
      const btnHide = document.getElementById('btn-hide-ui');
      if (btnHide) btnHide.textContent = dict.controls.hideUi;
    }
  };

  const handleSideToggle = () => {
    setPlayingAsWhite((prev) => !prev);
    setMobileSheetOpen(false);
  };

  return (
    <ErrorBoundary>
      <div id="loading-overlay">
        <div className="loader-title">{dict.brand.loadingTitle}</div>
        <div className="loader-bar-wrap">
          <div className="loader-bar" id="loader-bar"></div>
        </div>
        <div id="loader-text">{dict.brand.loadingSubtitle}</div>
      </div>

      <div id="canvas-container"></div>

      <button
        type="button"
        className="hud-btn mobile-only-restore-ui"
        id="btn-mobile-show-ui"
        onClick={handleRestoreUI}
        title={dict.controls.showUi}
      >
        {dict.controls.showUi}
      </button>

      <div id="hud-top">
        <div className="hud-group" id="hud-left">
          <div className="brand-pill">
            <span className="brand-title">{dict.brand.title}</span>
          </div>
          <div className="status-pill" id="status-pill">
            <span className="turn-dot" id="turn-dot"></span>
            <span id="turn-text">{dict.turn.white}</span>
            <span className="mode-badge" id="mode-badge">
              {playingAsWhite ? dict.turn.playingAsWhite : dict.turn.playingAsBlack}
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
            title={playingAsWhite ? dict.controls.playAsBlack : dict.controls.playAsWhite}
            onClick={handleSideToggle}
          >
            {playingAsWhite ? dict.controls.playAsBlack : dict.controls.playAsWhite}
          </button>
          <button
            className="hud-btn"
            id="btn-ai-move"
            title={dict.controls.aiMove}
            onClick={() => setMobileSheetOpen(false)}
          >
            {dict.controls.aiMove}
          </button>
          <button
            className="hud-btn"
            id="btn-reset"
            title={dict.controls.newGame}
            onClick={() => setMobileSheetOpen(false)}
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
          >
            {dict.controls.camPlayer}
          </button>
          <button
            className="hud-btn"
            id="btn-cam-top"
            title={dict.controls.camOverhead}
          >
            {dict.controls.camOverhead}
          </button>
          <button
            className="hud-btn"
            id="btn-cam-side"
            title={dict.controls.camSide}
          >
            {dict.controls.camSide}
          </button>
          <button
            className="hud-btn"
            id="btn-cam-wide"
            title={dict.controls.camCathedral}
          >
            {dict.controls.camCathedral}
          </button>

          <div className="hud-divider" aria-hidden="true"></div>
          <div className="mobile-sheet-section-label">{dict.controls.displayAndGestures}</div>

          <button
            className="hud-btn"
            id="btn-hide-ui"
            title={dict.controls.hideUi}
            onClick={() => setMobileSheetOpen(false)}
          >
            {dict.controls.hideUi}
          </button>

          <div className="mobile-sheet-hint">
            {dict.controls.touchHint}
          </div>
        </div>
      </div>

      <div id="hud-bottom">
        <div className="hint-pill" id="controls-hint">
          {dict.controls.desktopHint}
        </div>
        <div className="captured-pill" id="captured-tray"></div>
      </div>

      <div id="checkmate-overlay" role="status" aria-live="polite">
        <div className="checkmate-banner">
          <div className="checkmate-ornament">{dict.dialog.judgment}</div>
          <div className="checkmate-crown" id="checkmate-crown">♔</div>
          <div className="checkmate-title" id="checkmate-title">{dict.dialog.checkmate}</div>
          <div className="checkmate-rule"></div>
          <div className="checkmate-subtitle" id="checkmate-subtitle">
            {dict.dialog.whiteWins}
          </div>
          <div className="checkmate-actions">
            <button className="checkmate-btn" id="btn-checkmate-replay">
              {dict.dialog.replayKingFall}
            </button>
            <button className="checkmate-btn" id="btn-checkmate-newgame">
              {dict.controls.newGame}
            </button>
            <button className="checkmate-btn secondary" id="btn-checkmate-dismiss">
              {dict.dialog.dismiss}
            </button>
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}
