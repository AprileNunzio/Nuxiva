import { useState, useEffect } from 'react';
import { i18n } from '../i18n/i18nService';
import { TranslationDictionary } from '../i18n/types';

interface Props {
  onReplay: () => void;
  onNewGame: () => void;
  onDismiss: () => void;
}

export function CheckmateModal({ onReplay, onNewGame, onDismiss }: Props) {
  const [dict, setDict] = useState<TranslationDictionary>(i18n.getDictionary());

  useEffect(() => {
    return i18n.subscribe((_, newDict) => {
      setDict(newDict);
    });
  }, []);

  return (
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
          <button className="checkmate-btn" id="btn-checkmate-replay" onClick={onReplay}>
            {dict.dialog.replayKingFall}
          </button>
          <button className="checkmate-btn" id="btn-checkmate-newgame" onClick={onNewGame}>
            {dict.controls.newGame}
          </button>
          <button className="checkmate-btn secondary" id="btn-checkmate-dismiss" onClick={onDismiss}>
            {dict.dialog.dismiss}
          </button>
        </div>
      </div>
    </div>
  );
}
